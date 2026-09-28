Implement PLAN.md task 2 only, in this worktree.

Create exactly:
- brainfm_tui/session.py
- tests/test_session.py

Paste the test and the implementation from PLAN.md task 2. Do not redesign them.

Red: `uv run pytest tests/test_session.py::test_load_token_unwraps_double_encoded_jwt -v` fails because the module is missing.
Green: `uv run pytest tests/test_session.py -q` prints `5 passed`.

Commit only those two files:
git add brainfm_tui/session.py tests/test_session.py
git commit -m "Decode the local session and track URLs"

Do not push. Do not merge. Do not edit any other file. Do not read the WebKit cookie file. Do not print a real JWT. Reply with the pytest summary and the commit hash.
