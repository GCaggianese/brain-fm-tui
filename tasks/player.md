Implement PLAN.md task 4 only, in this worktree.

Create exactly:
- brainfm_tui/player.py
- tests/test_player.py

Paste the test and the implementation from PLAN.md task 4. Do not redesign them.

Red: `uv run pytest tests/test_player.py -v` fails because the module is missing.
Green: `uv run pytest tests/test_player.py -q` prints `2 passed`.

The tests must not start mpv. If mpv starts, you called Mpv.start from a test. Remove that call.

Commit only those two files:
git add brainfm_tui/player.py tests/test_player.py
git commit -m "Play stream URLs with one mpv process"

Do not push. Do not merge. Do not edit any other file. Reply with the pytest summary and the commit hash.
