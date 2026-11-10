# rewrite-en: Design

Requirements: [requirements.md](requirements.md) · Tasks: [tasks.md](tasks.md)

Each section names the requirements it satisfies. If the design changes, update this file in the same change as the code.

## Architecture

```
pynput Listener (listener thread)
  ├─ ModifierTracker      ← tracks held modifiers          (REQ-HK-1)
  └─ HotKey → on_activate → worker thread                  (REQ-HK-4)
                               └─ RewritePipeline.rewrite_selection()
                                    lock (non-blocking)     (REQ-HK-3)
                                    Keys / Clipboard        clipboard_io.py
                                    Rewriter                claude_client.py
                                    Feedback                feedback.py
```

`pipeline.py` depends only on four small protocols (`Clipboard`, `Keys`, `Rewriter`, `Feedback`) plus injectable `sleep` and `clock`, so all of its behaviour is unit-tested with fakes and no real keyboard.

| Module | Responsibility | Requirements |
|---|---|---|
| `pipeline.py` | One hotkey press, end to end; overlap lock; restore on every path | REQ-HK-1, REQ-HK-3, REQ-CAP-1, REQ-CAP-2, REQ-PST-1, REQ-PST-2, REQ-FB-1, REQ-SEC-2 |
| `claude_client.py` | Build request, map API errors to codes, clean output | REQ-RW-1 … REQ-RW-6, REQ-SEC-2, REQ-SEC-3 |
| `prompts.py` | System prompt = fixed rules + writing style (default or from config), `<text>` wrapping | REQ-RW-1, REQ-RW-7, REQ-CFG-3 |
| `clipboard_io.py` | pyperclip clipboard, pynput copy/paste with Ctrl/Cmd, `ModifierTracker` | REQ-OS-1, REQ-HK-1, REQ-PST-3 |
| `app.py` | Listener, hotkey parse, worker thread, macOS permission check | REQ-HK-2, REQ-HK-4, REQ-OS-2 |
| `config.py` | Defaults per OS, TOML load and validation, default file | REQ-HK-2, REQ-CFG-1, REQ-CFG-2 |
| `keystore.py` | keyring then `ANTHROPIC_API_KEY` | REQ-SEC-1 |
| `feedback.py` | Sounds: `winsound` on Windows, `afplay` on macOS | REQ-FB-1 |
| `autostart.py` | Windows Startup `.vbs`; macOS LaunchAgent; restart the LaunchAgent after a hotkey change | REQ-OS-3, REQ-CLI-6 |
| `cli.py` | Subcommands, logging setup (HTTP libraries capped at WARNING) | REQ-CLI-1 … REQ-CLI-3, REQ-SEC-2 |
| `hotkey_setup.py` | Validate/normalise a hotkey string, turn recorded key events into a combo, rewrite only the `hotkey` line of config.toml | REQ-CLI-4, REQ-CLI-5 |

## Flow of one hotkey press

1. `feedback.started()`; wait for modifiers released (2 s timeout; on timeout clear the tracker and continue). (REQ-HK-1, REQ-FB-1)
2. Save the original clipboard as text (non-text reads as `""`). (REQ-PST-3)
3. Put an invisible unique marker on the clipboard, simulate copy, poll every 20 ms for up to 1 s. Marker still there or whitespace → restore, error. (REQ-CAP-1, REQ-CAP-2)
4. `rewriter.rewrite(selection)`; any `RewriteError` → restore, error. (REQ-RW-*)
5. Put the result on the clipboard, paste once, sleep 250 ms, restore, success. (REQ-PST-1)
6. Any unexpected exception at any step → restore, error. (REQ-PST-2)

Only lengths, durations and error codes are logged. (REQ-SEC-2)

## Claude request

```python
client.messages.create(
    model=config.model,                    # default claude-haiku-5-5
    max_tokens=2048,
    system=build_system_prompt(config.style),   # rules + writing style
    messages=[{"role": "user", "content": f"<text>\n{selection}\n</text>"}],
    output_config={"effort": config.effort},   # default "low"
)
```

Client: `anthropic.Anthropic(timeout=timeout_seconds, max_retries=1)`. Error mapping, most specific first: `AuthenticationError`→`auth`, `PermissionDeniedError`→`permission`, `NotFoundError`→`model_not_found`, `RateLimitError`→`rate_limited`, `BadRequestError`→`bad_request`, other `APIStatusError`→`http_<status>`, `APITimeoutError`→`timeout`, `APIConnectionError`→`network`. Then `stop_reason` `refusal`→`refusal`, `max_tokens`→`truncated`, empty → `empty_output`.

## Decisions

| # | Decision | Why | Requirements |
|---|---|---|---|
| D1 | No `temperature`; latency controlled with `output_config.effort = "low"` | `claude-haiku-5-5` and newer models reject non-default sampling parameters with a 400 | REQ-RW-1, REQ-NF-1 |
| D2 | One pynput `Listener` with `HotKey` + `canonical`, not `GlobalHotKeys` | The same listener feeds the modifier tracker; `canonical` normalises left/right modifiers | REQ-HK-1 |
| D3 | macOS default hotkey uses Ctrl+Shift, not Option | Option combinations can produce a different character and fail to match | REQ-HK-2 |
| D4 | Invisible unique marker instead of clearing the clipboard | Detects a copy even when the selection equals the old clipboard | REQ-CAP-1 |
| D5 | Windows autostart is a hidden `.vbs` in the Startup folder running `pythonw -m rewrite_en run` | A `.lnk` shortcut needs pywin32, outside the allowed dependencies; `pythonw` shows no console | REQ-OS-3 |
| D6 | macOS LaunchAgent runs `sys.executable -m rewrite_en run`; `install-autostart` prints the resolved python path | Permissions are granted to the real binary, which the user must find | REQ-OS-2, REQ-OS-3 |
| D7 | Only plain text clipboard is saved and restored | pyperclip is text-only; rich clipboard needs per-OS native code (out of scope) | REQ-PST-3 |
| D8 | `set-hotkey` validates with our own small parser instead of pynput's, and records keys through `Listener.canonical` | Pure-Python validation is unit-testable on any OS and gives clear error messages; `canonical` strips modifier effects (Ctrl+E is reported as `e`, not `\x05`) | REQ-CLI-4, REQ-CLI-5 |
| D9 | The config is edited line by line (regex on the `hotkey` line), not re-serialised | Keeps the user's comments and other settings; stdlib has no TOML writer and no new dependency is allowed | REQ-CLI-4 |
| D10 | The writing style is a separate, replaceable section of the system prompt; the safety rules (keep names/URLs/code, `<text>` is data, output only the rewrite) are fixed | Users can tune tone without being able to break in-place replacement or prompt-injection protection | REQ-RW-7, REQ-CFG-3 |

## Dependencies

Runtime: `pynput`, `pyperclip`, `anthropic` (≥2.7,<3), `keyring`, `platformdirs`. Dev: `pytest`. Adding a dependency needs a requirement or decision here first.
