"""Phase 0 spike: hotkey -> wait for modifiers -> copy -> read clipboard -> paste a fixed string.

No API call. Run on each OS, select text in Teams / Notepad / TextEdit / a browser,
press the hotkey, and check the selection is replaced by the fixed string.

    python scripts/spike.py                # default hotkey for this OS
    python scripts/spike.py "<ctrl>+<shift>+e"
"""

import sys
import threading
import time

import pyperclip
from pynput import keyboard

HOTKEY = sys.argv[1] if len(sys.argv) > 1 else (
    "<ctrl>+<shift>+e" if sys.platform == "darwin" else "<ctrl>+<alt>+e"
)
MOD = keyboard.Key.cmd if sys.platform == "darwin" else keyboard.Key.ctrl
MODS = {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.alt, keyboard.Key.alt_l,
        keyboard.Key.alt_r, keyboard.Key.alt_gr, keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
        keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r}
held, kb = set(), keyboard.Controller()


def combo(ch):
    with kb.pressed(MOD):
        kb.tap(ch)


def work():
    t0 = time.monotonic()
    while held and time.monotonic() - t0 < 2:
        time.sleep(0.01)
    print(f"modifiers released after {time.monotonic() - t0:.2f}s (still held: {held or 'none'})")
    original = pyperclip.paste()
    marker = "__spike_marker__"
    pyperclip.copy(marker)
    combo("c")
    t1 = time.monotonic()
    while pyperclip.paste() == marker and time.monotonic() - t1 < 1:
        time.sleep(0.02)
    selected = pyperclip.paste()
    if selected == marker:
        print("nothing selected (clipboard did not change)")
        pyperclip.copy(original)
        return
    print(f"copied {len(selected)} chars after {time.monotonic() - t1:.2f}s")
    pyperclip.copy(f"[SPIKE OK: {len(selected)} chars]")
    combo("v")
    time.sleep(0.25)
    pyperclip.copy(original)
    print("pasted fixed string, clipboard restored")


hk = keyboard.HotKey(keyboard.HotKey.parse(HOTKEY), lambda: threading.Thread(target=work, daemon=True).start())


def on_press(k):
    if k in MODS:
        held.add(k)
    hk.press(listener.canonical(k))


def on_release(k):
    held.discard(k)
    hk.release(listener.canonical(k))


with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print(f"Spike running. Select text, press {HOTKEY}. Ctrl+C to quit.")
    listener.join()
