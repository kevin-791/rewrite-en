"""Clipboard save/restore and simulated copy/paste, per OS.

Only plain text is supported: if the clipboard holds an image or files, it is
read as empty and cannot be restored (known MVP limitation, see README).
"""

from __future__ import annotations

import logging
import sys
import threading
import time

log = logging.getLogger(__name__)


class SystemClipboard:
    """Plain-text clipboard via pyperclip. Never raises on read."""

    def __init__(self):
        import pyperclip  # imported lazily so tests don't need a display

        self._pc = pyperclip

    def get(self) -> str:
        try:
            value = self._pc.paste()
        except Exception:  # pyperclip raises on non-text content on some setups
            log.debug("clipboard read failed", exc_info=True)
            return ""
        return value if isinstance(value, str) else ""

    def set(self, text: str) -> None:
        self._pc.copy(text)


class ModifierTracker:
    """Tracks which modifier keys are physically held, fed by the app's key listener."""

    def __init__(self):
        self._held: set = set()
        self._cond = threading.Condition()

    @staticmethod
    def _is_modifier(key) -> bool:
        from pynput.keyboard import Key

        modifiers = {
            Key.ctrl, Key.ctrl_l, Key.ctrl_r,
            Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr,
            Key.shift, Key.shift_l, Key.shift_r,
            Key.cmd, Key.cmd_l, Key.cmd_r,
        }
        return key in modifiers

    def on_press(self, key) -> None:
        if self._is_modifier(key):
            with self._cond:
                self._held.add(key)

    def on_release(self, key) -> None:
        if self._is_modifier(key):
            with self._cond:
                self._held.discard(key)
                self._cond.notify_all()

    def wait_released(self, timeout: float) -> bool:
        """Block until no modifier is held. Returns False on timeout."""
        with self._cond:
            ok = self._cond.wait_for(lambda: not self._held, timeout=timeout)
            if not ok:
                # A release can be missed (e.g. lock screen); don't stay stuck forever.
                self._held.clear()
            return ok


class KeySender:
    """Simulates Ctrl/Cmd+C and Ctrl/Cmd+V with pynput."""

    def __init__(self, tracker: ModifierTracker | None = None, platform: str | None = None):
        from pynput.keyboard import Controller, Key

        self._kb = Controller()
        self._mod = Key.cmd if (platform or sys.platform) == "darwin" else Key.ctrl
        self._tracker = tracker

    def wait_modifiers_released(self, timeout: float) -> bool:
        if self._tracker is None:
            return True
        return self._tracker.wait_released(timeout)

    def _combo(self, char: str) -> None:
        with self._kb.pressed(self._mod):
            time.sleep(0.02)
            self._kb.tap(char)
        time.sleep(0.02)

    def copy(self) -> None:
        self._combo("c")

    def paste(self) -> None:
        self._combo("v")
