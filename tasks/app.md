Implement PLAN.md task 6 only, in this worktree.

Create exactly:
- brainfm_tui/app.py
- tests/test_app.py

Paste both from PLAN.md task 6. Do not bind Enter on the App. OptionList already selects on Enter.

Red: `uv run pytest tests/test_app.py::test_lists_activities_and_enter_plays -v` fails because app is missing.
Green: `uv run pytest tests/test_app.py -q` prints `1 passed`.

runtime.py does not exist yet. Tests inject FakeBackend, so do not create runtime.py and do not import it.

Commit only those two files:
git add tests/test_app.py brainfm_tui/app.py
git commit -m "List activities in Textual"

Do not push. Do not merge. Do not edit any other file. Reply with the pytest summary and the commit hash.
