# rewrite-en: Smoke checklist (real machine)

Requirements: [requirements.md](requirements.md). Logic (clipboard restore, error paths, overlap lock, config, logging privacy) is covered by unit tests. This checklist covers only what needs a real keyboard, real apps, OS permissions and the real API. Run it on **Windows and macOS** before a release; about 10 minutes per OS.

Each case lists the requirement IDs it verifies (`tests/test_traceability.py` reads the `Verifies` column).

| Case | Steps | Expected | Verifies |
|---|---|---|---|
| S-1 | On a clean machine: `uv tool install .`, `rewrite-en set-key`, `rewrite-en test "xin chào, mình cần dời cuộc họp sang chiều mai"` | Prints a natural English sentence | REQ-OS-4 |
| S-2 | In Teams desktop, select a few Vietnamese lines that contain a link and an emoji, press the hotkey, then press Ctrl+Z / Cmd+Z | Replaced in place by English with the link, emoji and line breaks kept; undo brings the original back | REQ-OS-1, REQ-NF-2, REQ-NF-3 |
| S-3 | Copy an image, select some text, press the hotkey twice quickly | Exactly one rewrite, no crash, hotkey still responds afterwards | REQ-HK-4, REQ-PST-3 |
| S-4 | Rewrite a ~150-word paragraph 10 times | Median ≤ 3 s from hotkey to new text | REQ-NF-1 |
| S-5 | macOS only: turn off Accessibility or Input Monitoring for the terminal, run `rewrite-en run` | Warning naming the missing permission and the program path | REQ-OS-2 |
| S-6 | `rewrite-en install-autostart`, reboot, use the hotkey; then `uninstall-autostart`, reboot | Works after reboot with no console window; after uninstall it no longer starts | REQ-OS-3 |

## Results

| Case | Windows | macOS | Notes |
|---|---|---|---|
| S-1 … S-6 | not run | not run | |
