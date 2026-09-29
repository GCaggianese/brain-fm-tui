# brain-fm-tui

Textual player for the user's own Brain.fm subscription. Session is the file written by `--setup`. Audio goes through mpv. No browser window. No AUR package.

Spec: the code. Do not invent a login, a browser, or a desktop-app session.

## Hard rules

- Never print, log, or commit the JWT, the email, or a `tokenedUrl`. Stream URLs are credentials.
- Never read `/home/kang/.local/share/fm.brain.desktop`. Never launch `/usr/bin/brain-fm`, Chromium, Playwright, or a webview.
- Never add `requests`, `httpx`, `curl_cffi`, or `python-mpv`. Stdlib `urllib` and `socket` only, plus Textual.
- Never POST `/auth/email-login`. Never ask for a password.
- If `membership.isActive` is false, stop. Do not hunt for a bypass.
- Textual: no DataTable, no `width: auto` on a container, no App-level Enter binding. `OptionList` already handles Enter.
- Only edit files named in your task. Other agents own the rest.
- Commit on your branch. Do not push. Do not merge. Do not touch `main`.

## Verify

```sh
uv sync --python 3.14
uv run pytest -q
```

If Textual fails to import on 3.14, `uv sync --python /home/kang/.local/bin/python3.13` and continue. Do not debug Textual.

TDD is mandatory for the slice you were given: write the failing test, run it, implement the minimum, run it, commit.

## Layout

- `brainfm_tui/session.py` — token unwrap, track url/id, activity parse
- `brainfm_tui/api.py` — urllib calls to api.brain.fm
- `brainfm_tui/player.py` — one mpv process, JSON IPC
- `brainfm_tui/app.py` — Textual UI
- `brainfm_tui/runtime.py` — wires the three, written only after the others exist
