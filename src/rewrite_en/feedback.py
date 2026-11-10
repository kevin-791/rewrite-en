"""Short sounds: hotkey received, success, error. Never blocks the pipeline."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading

log = logging.getLogger(__name__)

_MAC_SOUNDS = {
    "started": "/System/Library/Sounds/Tink.aiff",
    "success": "/System/Library/Sounds/Glass.aiff",
    "error": "/System/Library/Sounds/Basso.aiff",
}


class SoundFeedback:
    def __init__(self, enabled: bool = True, platform: str | None = None):
        self.enabled = enabled
        self.platform = platform or sys.platform

    def _play(self, kind: str) -> None:
        if not self.enabled:
            return
        try:
            if self.platform == "win32":
                import winsound

                flag = {
                    "started": winsound.MB_OK,
                    "success": winsound.MB_ICONASTERISK,
                    "error": winsound.MB_ICONHAND,
                }[kind]
                threading.Thread(target=winsound.MessageBeep, args=(flag,), daemon=True).start()
            elif self.platform == "darwin":
                subprocess.Popen(
                    ["afplay", _MAC_SOUNDS[kind]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            log.debug("sound failed", exc_info=True)

    def started(self) -> None:
        self._play("started")

    def success(self) -> None:
        self._play("success")

    def error(self) -> None:
        self._play("error")


class SilentFeedback:
    def started(self) -> None: ...
    def success(self) -> None: ...
    def error(self) -> None: ...
