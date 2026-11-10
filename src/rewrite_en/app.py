"""Background app: register the global hotkey and run the pipeline in a worker thread."""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import sys
import threading

from rewrite_en.claude_client import ClaudeRewriter
from rewrite_en.clipboard_io import KeySender, ModifierTracker, SystemClipboard
from rewrite_en.config import Config
from rewrite_en.feedback import SoundFeedback
from rewrite_en.pipeline import RewritePipeline

log = logging.getLogger(__name__)


def macos_permission_problems() -> list[str]:
    """Return the missing macOS privacy permissions (empty list if all OK or unknown)."""
    if sys.platform != "darwin":
        return []
    problems = []
    try:
        ax = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        ax.AXIsProcessTrusted.restype = ctypes.c_bool
        if not ax.AXIsProcessTrusted():
            problems.append("Accessibility")
    except OSError:
        log.debug("could not check Accessibility", exc_info=True)
    try:
        iokit = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/IOKit.framework/IOKit")
        iokit.IOHIDCheckAccess.restype = ctypes.c_int
        iokit.IOHIDCheckAccess.argtypes = [ctypes.c_int]
        kIOHIDRequestTypeListenEvent = 1
        kIOHIDAccessTypeGranted = 0
        if iokit.IOHIDCheckAccess(kIOHIDRequestTypeListenEvent) != kIOHIDAccessTypeGranted:
            problems.append("Input Monitoring")
    except (OSError, AttributeError):
        log.debug("could not check Input Monitoring", exc_info=True)
    return problems


def run(config: Config, api_key: str) -> None:
    from pynput import keyboard

    problems = macos_permission_problems()
    if problems:
        import os

        msg = (
            "WARNING: macOS has not granted " + " and ".join(problems) + " to this program.\n"
            "The hotkey will silently do nothing until you allow it in\n"
            "System Settings > Privacy & Security for:\n"
            f"  {os.path.realpath(sys.executable)}\n"
            "(and for your terminal app when running from a terminal), then restart rewrite-en."
        )
        print(msg, file=sys.stderr)
        log.warning("missing macOS permissions: %s", ", ".join(problems))

    tracker = ModifierTracker()
    pipeline = RewritePipeline(
        clipboard=SystemClipboard(),
        keys=KeySender(tracker),
        rewriter=ClaudeRewriter(config, api_key),
        feedback=SoundFeedback(config.sounds),
    )

    def on_activate():
        if pipeline.busy:
            log.info("hotkey ignored: busy")
            return
        threading.Thread(target=pipeline.rewrite_selection, name="rewrite", daemon=True).start()

    try:
        hotkey = keyboard.HotKey(keyboard.HotKey.parse(config.hotkey), on_activate)
    except ValueError as e:
        raise SystemExit(f"Invalid hotkey {config.hotkey!r} in config: {e}")

    listener: keyboard.Listener

    def on_press(key):
        tracker.on_press(key)
        hotkey.press(listener.canonical(key))

    def on_release(key):
        tracker.on_release(key)
        hotkey.release(listener.canonical(key))

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    log.info("listening: hotkey=%s model=%s", config.hotkey, config.model)
    print(f"rewrite-en is running. Select text and press {config.hotkey}. Ctrl+C here to quit.")
    try:
        while listener.is_alive():
            listener.join(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        log.info("stopped")
