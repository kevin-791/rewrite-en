"""`set-hotkey`: validate, record and save the hotkey (REQ-CLI-4, REQ-CLI-5)."""

from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

from rewrite_en.config import config_path, write_default_config

MODIFIER_ORDER = ["ctrl", "alt", "shift", "cmd"]
_MODIFIER_ALIASES = {
    "ctrl": "ctrl", "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "alt": "alt", "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "shift": "shift", "shift_l": "shift", "shift_r": "shift",
    "cmd": "cmd", "cmd_l": "cmd", "cmd_r": "cmd",
}
# Named non-modifier keys that pynput's HotKey.parse accepts as <name>.
_NAMED_KEYS = {f"f{i}" for i in range(1, 21)} | {
    "space", "tab", "enter", "esc", "backspace", "delete", "insert",
    "home", "end", "page_up", "page_down", "up", "down", "left", "right",
}


class HotkeyError(ValueError):
    pass


def _token(part: str) -> tuple[str, str]:
    """Return ("mod", name) or ("key", pynput-form) for one '+'-separated part."""
    part = part.strip().lower()
    if not part:
        raise HotkeyError("empty key in combo (check for a stray '+')")
    if part.startswith("<") and part.endswith(">") and len(part) > 2:
        name = part[1:-1]
        if name in _MODIFIER_ALIASES:
            return "mod", _MODIFIER_ALIASES[name]
        if name in _NAMED_KEYS:
            return "key", f"<{name}>"
        raise HotkeyError(f"unknown key <{name}>")
    if len(part) == 1 and part.isprintable() and part != " ":
        return "key", part
    raise HotkeyError(f"unknown key {part!r} (modifiers need brackets, e.g. <ctrl>)")


def normalise_hotkey(raw: str) -> str:
    """Validate a pynput-style combo and return it in canonical order."""
    if not raw or not raw.strip():
        raise HotkeyError("empty hotkey")
    parts = raw.split("+")
    # "<ctrl>++" is ambiguous; we don't allow '+' itself as the key.
    mods: list[str] = []
    keys: list[str] = []
    for part in parts:
        kind, value = _token(part)
        target = mods if kind == "mod" else keys
        if value in target:
            raise HotkeyError(f"{value} appears twice")
        target.append(value)
    if not mods:
        raise HotkeyError("needs at least one modifier (<ctrl>, <alt>, <shift> or <cmd>)")
    if not keys:
        raise HotkeyError("needs one non-modifier key, e.g. e or <f9>")
    if len(keys) > 1:
        raise HotkeyError("needs exactly one non-modifier key")
    ordered = [f"<{m}>" for m in MODIFIER_ORDER if m in mods]
    return "+".join(ordered + keys)


def warnings_for(combo: str, platform: str | None = None) -> list[str]:
    platform = platform or sys.platform
    out = []
    if platform == "darwin" and "<alt>" in combo:
        out.append(
            "Option (<alt>) combos can type a special character on macOS and may not trigger; "
            "<ctrl>+<shift> or <cmd>+<shift> is safer."
        )
    return out


_HOTKEY_LINE = re.compile(r"^\s*hotkey\s*=.*$", re.MULTILINE)


def save_hotkey(combo: str, path: Path | None = None) -> Path:
    """Write `combo` to the config, changing only the hotkey line."""
    path = path or config_path()
    if not path.exists():
        write_default_config(path)
    text = path.read_text(encoding="utf-8")
    line = f'hotkey = "{combo}"'
    if _HOTKEY_LINE.search(text):
        text = _HOTKEY_LINE.sub(line, text, count=1)
    else:
        text = line + "\n" + text
    path.write_text(text, encoding="utf-8")
    return path


def combo_from_events(events) -> str | None:
    """Turn ("p"|"r", token) events into a combo string.

    Tokens are modifier names (ctrl/alt/shift/cmd) or a non-modifier key (single
    char, or a named key such as f9). The combo is the set of keys held together
    at the moment the last one is released; a tap without a modifier is ignored.
    """
    held: list[str] = []
    peak: list[str] = []
    for kind, tok in events:
        if kind == "p":
            if tok not in held:
                held.append(tok)
                if len(held) >= len(peak):
                    peak = list(held)
        else:
            if tok in held:
                held.remove(tok)
            if not held:
                combo = _peak_to_combo(peak)
                if combo:
                    return combo
                peak = []
    return None


def _peak_to_combo(keys: list[str]) -> str | None:
    parts = []
    for k in keys:
        if k in MODIFIER_ORDER:
            parts.append(f"<{k}>")
        elif len(k) == 1:
            parts.append(k.lower())
        else:
            parts.append(f"<{k}>")
    try:
        return normalise_hotkey("+".join(parts))
    except HotkeyError:
        return None


def record_hotkey(timeout: float = 10.0) -> str | None:
    """Listen to the real keyboard until a valid combo is pressed and released."""
    from pynput import keyboard

    events: list[tuple[str, str]] = []
    result: list[str] = []
    done = threading.Event()

    def to_token(key) -> str | None:
        name = getattr(key, "name", None)
        if name:  # Key enum member
            return _MODIFIER_ALIASES.get(name, name)
        char = getattr(key, "char", None)
        return char.lower() if char else None

    def handle(kind, key):
        tok = to_token(listener.canonical(key))
        if tok is None:
            return
        events.append((kind, tok))
        combo = combo_from_events(events)
        if combo:
            result.append(combo)
            done.set()
            return False  # stop listener

    listener = keyboard.Listener(
        on_press=lambda k: handle("p", k), on_release=lambda k: handle("r", k)
    )
    listener.start()
    done.wait(timeout)
    listener.stop()
    return result[0] if result else None
