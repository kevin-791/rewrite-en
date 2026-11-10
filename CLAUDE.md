# rewrite-en: working rules

This project uses **spec-driven development**. The specs in `specs/` are the source of truth; code follows them.

## Files

- `specs/requirements.md`: what the system does. Every requirement has a stable ID (`REQ-<AREA>-<n>`) in EARS phrasing.
- `specs/design.md`: how: modules, flow, the Claude request, and numbered decisions (`D<n>`) with the requirements they serve.
- `specs/tasks.md`: phased tasks, each citing the requirements it delivers, with status `[ ]` / `[~]` / `[x]`.
- `specs/manual-tests.md`: a short smoke checklist (`S-<n>`) for what unit tests can't reach (real keyboard, apps, OS permissions, real API), each citing requirement IDs. Keep it short: anything testable with fakes belongs in unit tests.

## Workflow for any change

1. **Spec first.** Add or edit the requirement in `requirements.md` (new ID for new behaviour; never reuse or renumber an ID, mark removed ones `~~REQ-…~~ (removed)` instead of deleting the row). Update `design.md` if the design or a decision changes, and add a task in `tasks.md`.
2. **Test next.** Write or update tests tagged `@pytest.mark.req("REQ-…")`. Only when a real machine is truly needed, cite the ID in a smoke case in `manual-tests.md` instead.
3. **Code last.** Implement until the tests pass.
4. **Gate.** `pytest` must be green. `tests/test_traceability.py` fails if any requirement has no automated or manual test, or a test cites an ID that doesn't exist.
5. A PR description lists the requirement IDs it adds or changes.

If code and spec disagree, the spec wins: fix the code, or change the spec in the same PR and say why.

## Commands

```bash
uv venv && uv pip install -e '.[dev]'
.venv/bin/pytest                  # unit tests + traceability gate
python scripts/spike.py           # Phase 0 spike on a real machine
```

## Constraints

- Python 3.11+. Runtime deps only: pynput, pyperclip, anthropic, keyring, platformdirs (pytest for dev). A new dependency needs a decision in `design.md` and the user's OK.
- Never log selected text, results or the API key (REQ-SEC-2).
- Every error path restores the clipboard and leaves the original text alone (REQ-PST-2).
- Shared code for Windows and macOS; only Ctrl/Cmd keys, sounds and autostart are per-OS.
