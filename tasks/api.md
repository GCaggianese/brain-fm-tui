Implement PLAN.md task 3 only, in this worktree. Do not implement catalog (task 5). Another agent owns session.py; do not create it.

Create exactly:
- brainfm_tui/api.py
- tests/test_api.py

Paste the task 3 test and the task 3 implementation from PLAN.md. Stop before `catalog`. Do not add the `activities_from` import.

Red: `uv run pytest tests/test_api.py -v` fails because the module is missing.
Green: `uv run pytest tests/test_api.py -q` prints `2 passed`.

Commit only those two files:
git add brainfm_tui/api.py tests/test_api.py
git commit -m "Call api.brain.fm with a bearer token"

Do not push. Do not merge. Do not edit any other file. Do not call the real API. Do not print a token. Reply with the pytest summary and the commit hash.
