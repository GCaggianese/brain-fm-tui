# brain-fm-tui

Plays your Brain.fm subscription through mpv. No browser window.

The session is the JWT in WebKit localStorage (`persist:auth`), not the
cookie file. If the TUI says the session expired, open https://my.brain.fm
once and log in again.

```sh
uv run brain-fm-tui
```

Enter plays the highlighted station. Space pauses. n skips. q quits mpv too.
