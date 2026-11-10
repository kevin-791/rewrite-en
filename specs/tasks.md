# rewrite-en: Tasks

Requirements: [requirements.md](requirements.md) · Design: [design.md](design.md)

Tasks follow the plan's phases. A task is done when its code is merged **and** the requirements it lists are verified (automated test passing, or smoke case recorded in [manual-tests.md](manual-tests.md)). `[x]` = done, `[~]` = code done, verification on real machines pending, `[ ]` = not started.

## Phase 0: Risk spike

- [~] T0.1 `scripts/spike.py`: hotkey, wait for modifiers, copy, paste a fixed string. *Done when* the fixed string replaces a Teams selection on both OSes. (REQ-HK-1, REQ-OS-1)
- [ ] T0.2 Confirm default hotkeys per OS; update REQ-HK-2 and D3 if they change. (REQ-HK-2)

## Phase 1: Core pipeline

- [x] T1.1 `prompts.py`, `claude_client.py` with error mapping and clean-up. (REQ-RW-1 … REQ-RW-6)
- [x] T1.2 `clipboard_io.py`, `keystore.py`. (REQ-OS-1, REQ-SEC-1)
- [x] T1.3 `pipeline.RewritePipeline.rewrite_selection()`. (REQ-CAP-1, REQ-CAP-2, REQ-PST-1, REQ-PST-2)
- [~] T1.4 *Done when* a Vietnamese selection in Teams is replaced by English (S-2).

## Phase 2: App, config, CLI

- [x] T2.1 `app.py` with worker thread and overlap lock. (REQ-HK-3, REQ-HK-4)
- [x] T2.2 `config.py`, `cli.py`, `feedback.py`. (REQ-CFG-1, REQ-CFG-2, REQ-CLI-1, REQ-CLI-2, REQ-FB-1)
- [x] T2.4 Accept `-v` after the subcommand too (bug found on first real install). (REQ-CLI-3)
- [x] T2.5 `set-hotkey` command: validate, record, save, restart LaunchAgent. (REQ-CLI-4, REQ-CLI-5, REQ-CLI-6)
- [~] T2.3 *Done when* `set-key`, `test`, `run` work on a real machine (S-1, S-2).

## Phase 3: Errors and edge cases

- [x] T3.1 Unit tests for every error path restoring the clipboard. (REQ-PST-2, REQ-CAP-2, REQ-RW-2, REQ-RW-5)
- [~] T3.2 Smoke S-3 on both OSes.

## Phase 4: Install and autostart

- [x] T4.1 `pyproject.toml` entry points, `autostart.py`, README with macOS permissions. (REQ-OS-2, REQ-OS-3, REQ-OS-4)
- [~] T4.2 *Done when* S-1, S-5, S-6 pass on clean machines.

## Phase 5: Acceptance

- [x] T5.1 Automated tests and traceability check green (`pytest`).
- [ ] T5.2 Smoke checklist S-1 to S-6 on both OSes, results recorded. (REQ-NF-1, REQ-NF-2, REQ-NF-3)
