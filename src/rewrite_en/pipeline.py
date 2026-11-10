"""One hotkey press: capture selection -> Claude -> paste -> restore clipboard.

Everything OS-specific is injected (clipboard, keys, rewriter, feedback) so this
module is unit-testable without a real keyboard.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Protocol

from rewrite_en.claude_client import RewriteError

log = logging.getLogger(__name__)


class Clipboard(Protocol):
    def get(self) -> str: ...
    def set(self, text: str) -> None: ...


class Keys(Protocol):
    def wait_modifiers_released(self, timeout: float) -> bool: ...
    def copy(self) -> None: ...
    def paste(self) -> None: ...


class Rewriter(Protocol):
    def rewrite(self, text: str) -> str: ...


class Feedback(Protocol):
    def started(self) -> None: ...
    def success(self) -> None: ...
    def error(self) -> None: ...


class Outcome(enum.Enum):
    OK = "ok"
    BUSY = "busy"
    NO_SELECTION = "no_selection"
    ERROR = "error"


@dataclass(frozen=True)
class Timings:
    modifier_release_timeout: float = 2.0
    copy_timeout: float = 1.0
    poll_interval: float = 0.02
    # Target apps read the clipboard asynchronously after Ctrl/Cmd+V;
    # restoring too early pastes the old content.
    paste_settle: float = 0.25


class RewritePipeline:
    def __init__(
        self,
        clipboard: Clipboard,
        keys: Keys,
        rewriter: Rewriter,
        feedback: Feedback,
        timings: Timings = Timings(),
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.clipboard = clipboard
        self.keys = keys
        self.rewriter = rewriter
        self.feedback = feedback
        self.timings = timings
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def rewrite_selection(self) -> Outcome:
        """Run once. Returns BUSY immediately if a previous run is still going."""
        if not self._lock.acquire(blocking=False):
            log.info("hotkey ignored: previous rewrite still running")
            return Outcome.BUSY
        try:
            return self._run()
        finally:
            self._lock.release()

    def _capture_selection(self) -> str | None:
        marker = f"⁣rewrite-en-{uuid.uuid4().hex}⁣"
        self.clipboard.set(marker)
        self.keys.copy()
        deadline = self._clock() + self.timings.copy_timeout
        while True:
            value = self.clipboard.get()
            if value != marker:
                return value
            if self._clock() >= deadline:
                return None
            self._sleep(self.timings.poll_interval)

    def _run(self) -> Outcome:
        started = self._clock()
        self.feedback.started()
        if not self.keys.wait_modifiers_released(self.timings.modifier_release_timeout):
            log.warning("modifier keys still held after %.1fs; continuing", self.timings.modifier_release_timeout)

        original = self.clipboard.get()
        restored = False

        def restore():
            nonlocal restored
            if not restored:
                restored = True
                try:
                    self.clipboard.set(original)
                except Exception:
                    log.exception("failed to restore clipboard")

        try:
            selected = self._capture_selection()
            if selected is None or not selected.strip():
                log.info("no selection")
                restore()
                self.feedback.error()
                return Outcome.NO_SELECTION

            try:
                result = self.rewriter.rewrite(selected)
            except RewriteError as e:
                log.warning("rewrite failed: code=%s in_chars=%d", e.code, len(selected))
                restore()
                self.feedback.error()
                return Outcome.ERROR

            self.clipboard.set(result)
            self.keys.paste()
            self._sleep(self.timings.paste_settle)
            restore()
            self.feedback.success()
            log.info(
                "done: in_chars=%d out_chars=%d total_seconds=%.2f",
                len(selected), len(result), self._clock() - started,
            )
            return Outcome.OK
        except Exception as e:
            # Unexpected bug: never leave the marker or a half state on the clipboard.
            log.error("unexpected error: %s", type(e).__name__, exc_info=True)
            restore()
            self.feedback.error()
            return Outcome.ERROR
