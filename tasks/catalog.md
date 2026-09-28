Implement PLAN.md task 5 only, in this worktree.

Append to the existing files. Do not replace them. Do not touch session.py.
- tests/test_api.py: append the two catalog tests from PLAN.md task 5. FakeResponse is already in that file.
- brainfm_tui/api.py: append catalog() from PLAN.md task 5, including the activities_from import.

Red: `uv run pytest tests/test_api.py::test_catalog_embeds_activities_without_a_second_call -v` fails because catalog is missing.
Green: `uv run pytest -q` prints `11 passed`.

Commit only those two files:
git add tests/test_api.py brainfm_tui/api.py
git commit -m "List activities from mental states"

Do not push. Do not merge. Do not call the real API. Do not print a token. Reply with the pytest summary and the commit hash.
