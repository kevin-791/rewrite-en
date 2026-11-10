"""Load config.toml from the OS config directory, with per-OS defaults."""

from __future__ import annotations

import logging
import sys
import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path

from platformdirs import user_config_dir, user_log_dir

from rewrite_en import APP_NAME
from rewrite_en.prompts import DEFAULT_STYLE

log = logging.getLogger(__name__)

# Ctrl+Alt+E on Windows. On macOS, Option combinations can produce a different
# character and fail to match, so the default uses Ctrl+Shift (see plan, risks).
# Final values to be confirmed by the Phase 0 spike on real machines.
DEFAULT_HOTKEYS = {
    "win32": "<ctrl>+<alt>+e",
    "darwin": "<ctrl>+<shift>+e",
}


@dataclass(frozen=True)
class Config:
    hotkey: str
    model: str = "claude-haiku-5-5"
    max_chars: int = 6000
    timeout_seconds: float = 20.0
    max_tokens: int = 2048
    # Claude effort level. "low" keeps latency down for short rewrites.
    effort: str = "low"
    sounds: bool = True
    # Writing-style section of the system prompt (REQ-RW-7, REQ-CFG-3).
    style: str = DEFAULT_STYLE


def default_config(platform: str | None = None) -> Config:
    platform = platform or sys.platform
    return Config(hotkey=DEFAULT_HOTKEYS.get(platform, DEFAULT_HOTKEYS["win32"]))


def config_dir() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False))


def config_path() -> Path:
    return config_dir() / "config.toml"


def log_dir() -> Path:
    return Path(user_log_dir(APP_NAME, appauthor=False))


_TYPES = {f.name: f.type for f in fields(Config)}


def _coerce(name: str, value):
    kind = _TYPES[name]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be true or false")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return value
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{name} must be a positive number")
        return float(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def load_config(path: Path | None = None, platform: str | None = None) -> Config:
    """Return defaults overridden by values from the TOML file, if it exists."""
    cfg = default_config(platform)
    path = path or config_path()
    if not path.exists():
        return cfg
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    overrides = {}
    for key, value in data.items():
        if key not in _TYPES:
            log.warning("Ignoring unknown config key %r", key)
            continue
        overrides[key] = _coerce(key, value)
    return replace(cfg, **overrides)


def write_default_config(path: Path | None = None) -> Path:
    """Create a commented config file with the defaults, unless one exists."""
    path = path or config_path()
    if path.exists():
        return path
    cfg = default_config()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# rewrite-en settings. Restart rewrite-en after editing.\n"
        "# Hotkey syntax is pynput's: <ctrl>, <alt>, <shift>, <cmd> plus a key.\n"
        f'hotkey = "{cfg.hotkey}"\n'
        f'model = "{cfg.model}"   # or "claude-sonnet-5-5" for better style\n'
        f"max_chars = {cfg.max_chars}\n"
        f"timeout_seconds = {int(cfg.timeout_seconds)}\n"
        f'effort = "{cfg.effort}"   # low | medium | high\n'
        f"sounds = {'true' if cfg.sounds else 'false'}\n"
        "# Uncomment to replace the default writing style (the other prompt rules stay):\n"
        '# style = """\n# Use basic, natural English. Keep sentences short and friendly.\n# """\n',
        encoding="utf-8",
    )
    return path
