Implement PLAN.md task 7 only, in this worktree.

Create exactly brainfm_tui/runtime.py by pasting the task 7 code from PLAN.md.
Delete the unused `activities_for` import before committing. Do not leave it.

Do not call the real API. Do not print a token. Do not start mpv.

`uv run pytest -q` must still pass. Existing tests do not import runtime. Also run:
uv run python -c 'import brainfm_tui.runtime'

Commit only that file:
git add brainfm_tui/runtime.py
git commit -m "Connect the session, the API, and mpv"

Do not push. Do not merge. Do not edit any other file. Reply with the pytest summary and the commit hash.
