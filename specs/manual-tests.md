# rewrite-en: Manual test matrix

Requirements: [requirements.md](requirements.md). These cases cover what unit tests cannot: the real keyboard, clipboard, target apps and OS permissions. Run every case on **Windows and macOS** in **Teams desktop**; run M-01 to M-04 also in Teams web, Outlook, Slack and VS Code.

Each case lists the requirement IDs it verifies (`tests/test_traceability.py` reads the `Verifies` column). Record results in the table at the bottom when doing acceptance.

| Case | Steps | Expected | Verifies |
|---|---|---|---|
| M-01 | Select 1–2 Vietnamese sentences, press the hotkey | Replaced by natural English in exactly the selected spot | REQ-NF-2, REQ-PST-1, REQ-OS-1 |
| M-02 | Select awkward English | Only grammar and phrasing fixed, meaning kept | REQ-RW-1 |
| M-03 | Select several lines with bullets | Same number of lines and structure | REQ-RW-1 |
| M-04 | Select text with a link, emoji, code and a name | Those strings unchanged | REQ-RW-1 |
| M-05 | Select nothing, press the hotkey | Nothing changes, error sound, old clipboard intact | REQ-CAP-2 |
| M-06 | Select more than `max_chars` characters | No API call (log shows `too_long`), error sound, text intact | REQ-RW-2 |
| M-07 | Disconnect the network, or set a wrong API key | Error sound, text intact, log shows `network` / `auth` | REQ-RW-5 |
| M-08 | Press the hotkey twice quickly | The second press is ignored while the first runs | REQ-HK-3, REQ-HK-4 |
| M-09 | Press the hotkey and keep holding the modifiers a moment | The selection is still copied correctly | REQ-HK-1 |
| M-10 | Ctrl+Z / Cmd+Z right after a replacement | The original text comes back | REQ-NF-3 |
| M-11 | Copy an image, then select text and press the hotkey | No crash; image not restored (documented) | REQ-PST-3 |
| M-12 | macOS: remove Accessibility or Input Monitoring, run `rewrite-en run` in a terminal | Warning naming the missing permission and the program path | REQ-OS-2 |
| M-13 | Fresh machine: `uv tool install .`, `set-key`, `install-autostart`, reboot | Hotkey works without opening a terminal, no console window | REQ-OS-3, REQ-OS-4, REQ-SEC-1 |
| M-14 | `uninstall-autostart`, reboot | rewrite-en no longer starts | REQ-OS-3 |
| M-15 | Measure 10 rewrites of a ~150-word paragraph per OS | Median ≤ 3 s from hotkey to new text | REQ-NF-1 |
| M-16 | After M-01 to M-15, read the log file | No selected text, result or API key in the log | REQ-SEC-2 |
| M-17 | Change `hotkey` in config.toml, restart | The new hotkey works and the old one doesn't | REQ-HK-2 |

## Results

| Case | Windows | macOS | Notes |
|---|---|---|---|
| M-01 … M-17 | not run | not run | |
