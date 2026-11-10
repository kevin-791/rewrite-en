# rewrite-en: Requirements

Status: **Approved for MVP** · Source: [plan](https://claude.ai/artifact/WKLqKV9xvHpdgU7LJzPgwH) · Design: [design.md](design.md) · Tasks: [tasks.md](tasks.md)

This file is the source of truth for what rewrite-en does. Code and tests follow it, not the other way around. Every requirement has a stable ID. Each ID must be verified by at least one automated test (`@pytest.mark.req("ID")`) or one manual test case in [manual-tests.md](manual-tests.md). `tests/test_traceability.py` enforces this.

Requirements use [EARS](https://alistairmavin.com/ears/) phrasing: *WHEN* (event), *WHILE* (state), *IF … THEN* (unwanted behaviour), *WHERE* (feature/platform), or plain *shall* (always).

## Glossary

- **Selection**: the text highlighted in the focused app when the hotkey is pressed.
- **Original clipboard**: the plain-text clipboard content just before the hotkey was handled.
- **Error feedback**: the error sound plus a log line with an error code.

## 1. Scope

**In scope (MVP):** one global hotkey, one action (rewrite to English), in-place replacement in the focused app, Claude API, key in the OS keychain, install with `uv tool` / `pipx`, autostart, one TOML config file. Windows 10/11 and macOS.

**Out of scope:** preset popup, tray icon, other actions (shorten, tone, other languages), streaming, rich text (bold, @mention, links), Linux, packaged `.exe` / `.app`, rewrite history, telemetry.

## 2. Hotkey

| ID | Requirement |
|---|---|
| REQ-HK-1 | WHEN the configured hotkey is pressed, the system shall wait until all modifier keys are released, for at most 2 seconds, before simulating copy. |
| REQ-HK-2 | The hotkey shall be configurable, with default `<ctrl>+<alt>+e` on Windows and `<ctrl>+<shift>+e` on macOS. |
| REQ-HK-3 | WHILE a rewrite is in progress, the system shall ignore further hotkey presses. |
| REQ-HK-4 | The system shall process a hotkey press in a worker thread so the hotkey listener is never blocked. |

## 3. Capturing the selection

| ID | Requirement |
|---|---|
| REQ-CAP-1 | WHEN capturing, the system shall put a unique marker on the clipboard, simulate copy, and poll the clipboard for up to 1 second until it differs from the marker. A selection equal to the original clipboard shall still be detected. |
| REQ-CAP-2 | IF the clipboard still holds the marker after the timeout, or the copied text is only whitespace, THEN the system shall not call the API, shall not paste, shall restore the original clipboard and shall give error feedback. |

## 4. Rewriting with Claude

| ID | Requirement |
|---|---|
| REQ-RW-1 | The system shall send one non-streaming `messages.create` request with the configured model, `max_tokens` 2048, the fixed system prompt, and the selection wrapped in `<text>` tags as the only user message. It shall not send sampling parameters such as `temperature`. |
| REQ-RW-2 | IF the selection is longer than `max_chars` (default 6000) THEN the system shall not call the API and shall give error feedback. |
| REQ-RW-3 | The system shall strip surrounding whitespace from the result, and strip a wrapping code fence or wrapping quotes unless the selection itself was wrapped the same way. |
| REQ-RW-4 | IF the result is empty after clean-up, or the response stopped because of `refusal` or `max_tokens`, THEN the system shall treat it as an error and paste nothing. |
| REQ-RW-5 | IF the API call fails (network, timeout, 401, 403, 404, 429, 400, 5xx) THEN the system shall give error feedback with a distinct error code and leave the selection unchanged. The request timeout shall be `timeout_seconds` (default 20) with at most 1 retry. |
| REQ-RW-6 | The system shall use only `text` content blocks of the response as the result (thinking blocks are ignored). |

## 5. Pasting and restoring

| ID | Requirement |
|---|---|
| REQ-PST-1 | WHEN a rewrite succeeds, the system shall put the result on the clipboard, simulate paste exactly once, wait at least 150 ms, then restore the original clipboard and give success feedback. |
| REQ-PST-2 | IF any step fails, including unexpected exceptions, THEN the system shall restore the original clipboard and shall not paste. |
| REQ-PST-3 | IF the original clipboard holds non-text content (image, files) THEN the system shall not crash; restoring that content is not required (documented limitation). |

## 6. Configuration

| ID | Requirement |
|---|---|
| REQ-CFG-1 | The system shall read `config.toml` from the OS config directory (via `platformdirs`), apply its values over the defaults, ignore unknown keys, and reject invalid values with an error. |
| REQ-CFG-2 | WHEN `run` or `config` starts and no config file exists, the system shall create one with the defaults; it shall never overwrite an existing file. |

## 7. Security and privacy

| ID | Requirement |
|---|---|
| REQ-SEC-1 | The system shall store the API key in the OS keychain (`keyring`) and read it from there first, falling back to `ANTHROPIC_API_KEY`. It shall never store the key in the config file. |
| REQ-SEC-2 | Logs and error messages shall never contain the selection, the result or the API key; they may contain lengths, durations and error codes. |
| REQ-SEC-3 | The system shall send only the selection to the API, nothing else from the screen or clipboard. |

## 8. Feedback

| ID | Requirement |
|---|---|
| REQ-FB-1 | The system shall play a short sound when it starts handling a hotkey press, and a distinct sound for success and for error. Sounds can be turned off in config. |

## 9. Command line

| ID | Requirement |
|---|---|
| REQ-CLI-1 | The `rewrite-en` command shall provide `run`, `set-key`, `test "text"`, `config`, `install-autostart` and `uninstall-autostart`. |
| REQ-CLI-2 | `rewrite-en test "text"` shall print the rewrite of the text without using the hotkey or the clipboard, and exit non-zero with the error code on failure. |

## 10. Platform

| ID | Requirement |
|---|---|
| REQ-OS-1 | WHERE the OS is Windows the system shall simulate Ctrl+C / Ctrl+V; WHERE the OS is macOS it shall simulate Cmd+C / Cmd+V. |
| REQ-OS-2 | WHERE the OS is macOS, WHEN `run` starts without Accessibility or Input Monitoring permission, the system shall print a clear warning naming the missing permission and the program to grant it to. |
| REQ-OS-3 | `install-autostart` shall make rewrite-en start at login without a visible console (Windows: Startup folder; macOS: LaunchAgent with `RunAtLoad`), and `uninstall-autostart` shall undo it. |
| REQ-OS-4 | The system shall install with a single `uv tool install .` or `pipx install .`. |

## 11. Non-functional

| ID | Requirement |
|---|---|
| REQ-NF-1 | For a selection of about 150 words on a normal network, the median time from hotkey to new text shall be at most 3 seconds (10 runs per OS). |
| REQ-NF-2 | The system shall work in Microsoft Teams desktop on both Windows and macOS. |
| REQ-NF-3 | Ctrl+Z / Cmd+Z right after a replacement shall bring back the original text in the target app. |
