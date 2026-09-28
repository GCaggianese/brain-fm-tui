# brain-fm API TUI

Supersedes both earlier plans. Do not implement those.

- `/home/kang/.hermes/plans/2026-09-28_171500-brain-fm-tui.md` drives the AUR app over MPRIS.
- `/home/kang/.hermes/plans/2026-09-28_171200-brain-fm-standalone-tui.md` hides a Chromium window.

This plan does neither. No browser window. No AUR process.

## Goal

A Python Textual TUI that plays the user's own Brain.fm subscription by calling `api.brain.fm` with the session the web app already stored, and streaming the returned URL through `mpv`.

## Current context / assumptions

Verified on this machine, 2026-09-28. Do not re-derive it by dumping secrets.

The Netscape cookie file `/home/kang/.local/share/fm.brain.desktop/cookies` is the wrong store. It has a cookie named `token` that is a JWT, and it is **not** the bearer token the web app sends. Analytics cookies live in that file too. Do not parse it. Do not print it. Do not copy it into the repo.

The bearer token is in WebKit localStorage:

- File: `/home/kang/.local/share/fm.brain.desktop/localstorage/https_my.brain.fm_0.localstorage`
- SQLite table `ItemTable(key TEXT, value BLOB)`
- Key: `persist:auth`
- Value encoding: UTF-16-LE JSON
- Field `token` is double-encoded: a string that itself starts and ends with `"`. `json.loads` that string once more. The result is a JWT (`eyJ`, two dots).
- Field `type` decodes to `email`. That is not a secret. Do not print the token, the email, or any other field value from this database.

Public app bundle `https://my.brain.fm/assets/index-BVKd1DYp.js` (fetched read-only, 4.4 MB) defines:

- `API_BASE_URL = "https://api.brain.fm/v2"`
- `API_V3_BASE_URL = "https://api.brain.fm/v3"`
- `getBaseUrl(3)` returns v3, anything else returns v2
- `BROWSER_TRACK_URL = "https://audio.brain.fm/"`
- Every API call sends `Authorization: Bearer <auth.token>` and `Content-Type: application/json`
- `GET /users/me` is api version 2. Response is used as `{user, membership}`.
- `GET /mentalStates/dynamic` lists modes. `GET /mentalStates/dynamic/${id}/activities` lists stations. The session-create code path passes api version 3 for dynamic endpoints. Use v3 for those.
- `POST /users/${userId}/sessions?platform=web` with body `{"dynamicActivityId": "<id>", "version": 3}`, api version 3. Response `result` has `dynamicActivity` and `servings`. The app then does `receiveQueue(result.servings)`.
- Track URL, from `getTrackVariationUrl` in that bundle: if the object has a `track` key, use `trackVariation.tokenedUrl`. Otherwise use `serving.trackVariation.tokenedUrl`, else `https://audio.brain.fm/` plus `url`.
- Track id, from `getTrackId`: `track.id` if `track` in the object, else `serving.track.id`.
- Next track: `POST /users/${userId}/sessions/tracks/${trackId}?platform=web` with an empty body, api version 3. Response `result.servings[0]` is the next item.

Playback tool already installed: `/usr/bin/mpv` (0.41.0). Do not add `python-mpv`, `requests`, or `httpx`. Use stdlib `urllib` and stdlib `socket` for mpv's JSON IPC. Python is 3.14.7. Textual is not installed; pin `textual==8.2.8`. Fallback interpreter if that import fails: `/home/kang/.local/bin/python3.13`.

Project directory: `/home/kang/PARA/3_Resources/Apps/brain-fm-tui`.

This uses the account the user already logged into. It does not log in, does not ask for a password, and does not bypass a paywall. If `membership.isActive` is false, stop. The server still decides whether a stream URL is issued.

## Architecture / proposed approach

Read the JWT from localStorage, call the three endpoints above with `urllib`, and hand `tokenedUrl` to one long-lived `mpv` process. Textual lists the activities and sends play, pause, and next. The browser is not launched. The AUR binary is not launched.

## Do not build

- Do not read `/home/kang/.local/share/fm.brain.desktop/cookies`.
- Do not print, log, or commit the JWT, the email, or a stream URL that contains a token. Stream URLs are capabilities. Keep them in the mpv process, not in the TUI log.
- Do not POST `/auth/email-login`. Do not add a password prompt.
- Do not launch `/usr/bin/brain-fm`, Chromium, Playwright, or a webview.
- Do not call `playerctl` or publish MPRIS.
- Do not add `requests`, `httpx`, `curl_cffi`, or `python-mpv`.
- Do not add genre filters, volume, album art, a DataTable, or `width: auto` on a Textual container.
- Do not `pacman -R` the AUR package. The user may still open it once if the JWT has expired.

Skipped: desktop media keys. Add a Python MPRIS publisher only if asked.

## Step-by-step tasks

Work in `/home/kang/PARA/3_Resources/Apps/brain-fm-tui`. After the scaffold, each task is red, then green, then one commit.

### 1. Scaffold

```bash
mkdir -p /home/kang/PARA/3_Resources/Apps/brain-fm-tui/brainfm_tui /home/kang/PARA/3_Resources/Apps/brain-fm-tui/tests
cd /home/kang/PARA/3_Resources/Apps/brain-fm-tui
git init
```

Write `pyproject.toml`:

```toml
[project]
name = "brain-fm-tui"
version = "0.1.0"
description = "Textual Brain.fm player. Uses the local session and mpv. No browser window."
requires-python = ">=3.12"
dependencies = ["textual==8.2.8"]

[project.scripts]
brain-fm-tui = "brainfm_tui.app:main"

[dependency-groups]
dev = ["pytest==8.4.2"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["brainfm_tui"]
```

Write `.gitignore`:

```
.venv/
__pycache__/
.pytest_cache/
*.egg-info/
dist/
```

Write `brainfm_tui/__init__.py` empty.

Write `brainfm_tui/__main__.py`:

```python
from brainfm_tui.app import main

if __name__ == "__main__":
    main()
```

```bash
cd /home/kang/PARA/3_Resources/Apps/brain-fm-tui
uv sync --python 3.14
uv run python -c 'import textual; print(textual.__version__)'
```

Expected: `8.2.8`

If the import fails, `uv sync --python /home/kang/.local/bin/python3.13` and repeat. Do not debug Textual.

```bash
git add pyproject.toml .gitignore brainfm_tui/__init__.py brainfm_tui/__main__.py uv.lock
git commit -m "Scaffold brain-fm-tui"
```

### 2. Token unwrap and track URL

Write `tests/test_session.py`:

```python
import json

from brainfm_tui.session import Activity, load_token_from_bytes, track_id, track_url


def test_load_token_unwraps_double_encoded_jwt():
    jwt = "eyJhbGciOiJub25lIn0.e30.sig"
    raw = json.dumps({"token": json.dumps(jwt), "type": json.dumps("email")}).encode("utf-16-le")
    assert load_token_from_bytes(raw) == jwt


def test_track_url_serving_shape():
    item = {"serving": {"track": {"id": "t1"}, "trackVariation": {"tokenedUrl": "https://audio.brain.fm/a?t=1"}}}
    assert track_url(item) == "https://audio.brain.fm/a?t=1"
    assert track_id(item) == "t1"


def test_track_url_flat_shape():
    item = {"track": {"id": "t2"}, "trackVariation": {"tokenedUrl": "https://audio.brain.fm/b"}}
    assert track_url(item) == "https://audio.brain.fm/b"
    assert track_id(item) == "t2"


def test_track_url_relative_fallback():
    item = {"url": "files/x.mp3", "serving": {"track": {"id": "t3"}}}
    assert track_url(item) == "https://audio.brain.fm/files/x.mp3"


def test_activities_from_payload():
    from brainfm_tui.session import activities_from

    payload = [
        {"id": "focus", "displayValue": "Focus", "activities": [
            {"id": "dw", "displayValue": "Deep Work"},
        ]},
    ]
    assert activities_from(payload) == [Activity("focus", "Focus", "dw", "Deep Work")]
```

```bash
cd /home/kang/PARA/3_Resources/Apps/brain-fm-tui
uv run pytest tests/test_session.py::test_load_token_unwraps_double_encoded_jwt -v
```

Expected: fail, `ModuleNotFoundError: No module named 'brainfm_tui.session'`. Red.

Write `brainfm_tui/session.py`:

```python
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

LOCALSTORAGE = Path(
    "/home/kang/.local/share/fm.brain.desktop/localstorage/https_my.brain.fm_0.localstorage"
)
AUDIO_BASE = "https://audio.brain.fm/"


@dataclass(frozen=True)
class Activity:
    mental_state_id: str
    mental_state: str
    activity_id: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.mental_state}  ·  {self.name}"


def load_token_from_bytes(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-16-le"))
    token = data["token"]
    if isinstance(token, str) and token[:1] == '"':
        token = json.loads(token)
    if not isinstance(token, str) or token.count(".") != 2:
        raise ValueError("persist:auth token is not a JWT")
    return token


def load_token(path: Path = LOCALSTORAGE) -> str:
    uri = f"file:{path}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
        row = con.execute("SELECT value FROM ItemTable WHERE key='persist:auth'").fetchone()
    except sqlite3.OperationalError:
        # ponytail: copy db+wal+shm only if the live file is locked; do not write into the WebKit dir
        raise
    if row is None:
        raise ValueError(f"no persist:auth in {path}; open https://my.brain.fm once and log in")
    blob = row[0]
    if isinstance(blob, str):
        blob = blob.encode()
    return load_token_from_bytes(blob)


def _serving(item: dict) -> dict:
    if "track" in item:
        return item
    serving = item.get("serving")
    return serving if isinstance(serving, dict) else {}


def track_id(item: dict) -> str:
    track = _serving(item).get("track") or {}
    return str(track.get("id") or "")


def track_url(item: dict) -> str:
    variation = _serving(item).get("trackVariation") or {}
    url = variation.get("tokenedUrl") or ""
    if not url:
        url = str(item.get("url") or "")
    if not url:
        raise ValueError("serving has no track url")
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return AUDIO_BASE + url.lstrip("/")


def track_name(item: dict) -> str:
    track = _serving(item).get("track") or {}
    return str(track.get("name") or track.get("title") or "")


def _as_list(payload, *keys: str) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def activities_from(payload) -> list[Activity]:
    found: list[Activity] = []
    states = _as_list(payload, "mentalStates", "dynamicMentalStates", "result")
    for state in states:
        if not isinstance(state, dict):
            continue
        state_id = str(state.get("id") or "")
        state_name = str(state.get("displayValue") or state.get("name") or state_id)
        nested = state.get("activities") or state.get("dynamicActivities") or []
        if not nested:
            found.append(Activity(state_id, state_name, state_id, state_name))
            continue
        for activity in nested:
            if not isinstance(activity, dict):
                continue
            found.append(Activity(
                state_id,
                state_name,
                str(activity.get("id") or ""),
                str(activity.get("displayValue") or activity.get("name") or "untitled"),
            ))
    return [item for item in found if item.activity_id]
```

The `activities_from` nested case is what the unit test hits. The no-nested case is for a mental-state list that does not embed activities; task 4 fetches activities per state if the first payload has no `activity_id` distinct from the state. Do not invent a third shape.

```bash
uv run pytest tests/test_session.py -q
```

Expected: `5 passed`.

```bash
git add tests/test_session.py brainfm_tui/session.py
git commit -m "Decode the local session and track URLs"
```

### 3. API client against a fake HTTP response

Write `tests/test_api.py`:

```python
import json
from io import BytesIO

from brainfm_tui.api import AuthExpired, get_json


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._raw = json.dumps(payload).encode()

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_get_json_unwraps_result_and_sends_bearer():
    seen = {}

    def opener(req, timeout):
        seen["url"] = req.full_url
        seen["auth"] = req.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse(200, {"result": {"user": {"id": "u1"}}})

    assert get_json("GET", "https://api.brain.fm/v2/users/me", "eyJ.e30.sig", opener=opener) == {"user": {"id": "u1"}}
    assert seen["auth"] == "Bearer eyJ.e30.sig"
    assert seen["timeout"] == 20


def test_get_json_401_is_auth_expired():
    import urllib.error

    def opener(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "no", hdrs=None, fp=BytesIO(b""))

    try:
        get_json("GET", "https://api.brain.fm/v2/users/me", "eyJ.e30.sig", opener=opener)
    except AuthExpired as exc:
        assert "my.brain.fm" in str(exc)
    else:
        raise AssertionError("expected AuthExpired")
```

```bash
uv run pytest tests/test_api.py -v
```

Expected: fail, `brainfm_tui.api` missing. Red.

Write `brainfm_tui/api.py`:

```python
import json
import urllib.error
import urllib.request

V2 = "https://api.brain.fm/v2"
V3 = "https://api.brain.fm/v3"


class AuthExpired(Exception):
    pass


def get_json(method: str, url: str, token: str, body=None, opener=urllib.request.urlopen):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "brain-fm-tui",
        },
    )
    try:
        with opener(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise AuthExpired("session expired; open https://my.brain.fm once, then retry") from exc
        detail = exc.read().decode(errors="replace")[:180]
        raise RuntimeError(f"{method} {url} -> {exc.code} {detail}") from exc
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"]
    return payload


def users_me(token: str, opener=urllib.request.urlopen) -> dict:
    return get_json("GET", f"{V2}/users/me", token, opener=opener)


def mental_states(token: str, opener=urllib.request.urlopen):
    return get_json("GET", f"{V3}/mentalStates/dynamic", token, opener=opener)


def activities_for(token: str, mental_state_id: str, opener=urllib.request.urlopen):
    return get_json(
        "GET",
        f"{V3}/mentalStates/dynamic/{mental_state_id}/activities",
        token,
        opener=opener,
    )


def start_session(token: str, user_id: str, activity_id: str, opener=urllib.request.urlopen) -> dict:
    return get_json(
        "POST",
        f"{V3}/users/{user_id}/sessions?platform=web",
        token,
        body={"dynamicActivityId": activity_id, "version": 3},
        opener=opener,
    )


def next_serving(token: str, user_id: str, track_id: str, opener=urllib.request.urlopen) -> dict:
    return get_json(
        "POST",
        f"{V3}/users/{user_id}/sessions/tracks/{track_id}?platform=web",
        token,
        body={},
        opener=opener,
    )
```

```bash
uv run pytest tests/test_api.py tests/test_session.py -q
```

Expected: `7 passed`.

```bash
git add tests/test_api.py brainfm_tui/api.py
git commit -m "Call api.brain.fm with a bearer token"
```

### 4. mpv command builder, no real playback in tests

Write `tests/test_player.py`:

```python
from brainfm_tui.player import ipc_payload, mpv_argv


def test_mpv_argv_is_one_quiet_process():
    argv = mpv_argv("/tmp/brainfm-mpv.sock", "https://audio.brain.fm/x")
    assert argv[0] == "mpv"
    assert "--no-video" in argv
    assert "--input-ipc-server=/tmp/brainfm-mpv.sock" in argv
    assert argv[-1] == "https://audio.brain.fm/x"


def test_ipc_payload_is_one_json_line():
    raw = ipc_payload(["loadfile", "https://audio.brain.fm/x", "replace"])
    assert raw.endswith(b"\n")
    assert b"loadfile" in raw
```

```bash
uv run pytest tests/test_player.py -v
```

Expected: fail, module missing. Red.

Write `brainfm_tui/player.py`:

```python
import json
import socket
import subprocess
from pathlib import Path

SOCK = Path.home() / ".local/share/brain-fm-tui/mpv.sock"


def mpv_argv(sock: str, url: str) -> list[str]:
    return [
        "mpv",
        "--no-video",
        "--really-quiet",
        "--no-terminal",
        f"--input-ipc-server={sock}",
        url,
    ]


def ipc_payload(command: list) -> bytes:
    return json.dumps({"command": command}).encode() + b"\n"


class Mpv:
    def __init__(self, sock: Path = SOCK):
        self.sock = sock
        self.proc: subprocess.Popen | None = None

    def start(self, url: str) -> None:
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        if self.sock.exists():
            self.sock.unlink()
        self.proc = subprocess.Popen(mpv_argv(str(self.sock), url))

    def _ipc(self, command: list) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect(str(self.sock))
            sock.sendall(ipc_payload(command))
            sock.recv(4096)

    def load(self, url: str) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self.start(url)
            return
        self._ipc(["loadfile", url, "replace"])
        self._ipc(["set_property", "pause", False])

    def toggle(self) -> None:
        self._ipc(["cycle", "pause"])

    def close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
```

`load` starts mpv the first time and uses `loadfile` after that, so next-track does not leak a second process. `sock.recv` is required; mpv's IPC blocks if the reply is never read.

```bash
uv run pytest -q
```

Expected: `9 passed`. This must not start mpv. If mpv starts, a test called `Mpv.start`. Stop and remove that call.

```bash
git add tests/test_player.py brainfm_tui/player.py
git commit -m "Play stream URLs with one mpv process"
```

### 5. Catalog loader

The mental-state payload may or may not embed activities. One function covers both, and it is the only place that decides to call `activities_for`.

Append to `tests/test_api.py`:

```python
from brainfm_tui.api import catalog
from brainfm_tui.session import Activity


def test_catalog_embeds_activities_without_a_second_call():
    def opener(req, timeout):
        assert req.full_url.endswith("/mentalStates/dynamic")
        return FakeResponse(200, {"result": [
            {"id": "focus", "displayValue": "Focus", "activities": [
                {"id": "dw", "displayValue": "Deep Work"},
            ]},
        ]})

    assert catalog("tok", opener=opener) == [Activity("focus", "Focus", "dw", "Deep Work")]


def test_catalog_fetches_activities_when_states_have_none():
    def opener(req, timeout):
        if req.full_url.endswith("/mentalStates/dynamic"):
            return FakeResponse(200, {"result": [{"id": "focus", "displayValue": "Focus"}]})
        assert req.full_url.endswith("/mentalStates/dynamic/focus/activities")
        return FakeResponse(200, {"result": [{"id": "dw", "displayValue": "Deep Work"}]})

    assert catalog("tok", opener=opener) == [Activity("focus", "Focus", "dw", "Deep Work")]
```

`FakeResponse` is already in that file from task 3.

```bash
uv run pytest tests/test_api.py::test_catalog_embeds_activities_without_a_second_call -v
```

Expected: fail, `catalog` missing. Red.

Append to `brainfm_tui/api.py`:

```python
from brainfm_tui.session import Activity, activities_from


def catalog(token: str, opener=urllib.request.urlopen) -> list[Activity]:
    states = mental_states(token, opener=opener)
    embedded = activities_from(states)
    if embedded and any(item.activity_id != item.mental_state_id for item in embedded):
        return embedded
    found: list[Activity] = []
    for state in embedded:
        nested = activities_from([
            {"id": state.mental_state_id, "displayValue": state.mental_state,
             "activities": activities_for(token, state.mental_state_id, opener=opener)},
        ])
        found.extend(nested or [state])
    return found
```

If `activities_from` on a bare state list returns `Activity(id, name, id, name)`, `activity_id == mental_state_id`, so the second branch runs. That is the condition. Do not add a third.

```bash
uv run pytest -q
```

Expected: `11 passed`.

```bash
git add tests/test_api.py brainfm_tui/api.py
git commit -m "List activities from mental states"
```

### 6. Textual list

Write `tests/test_app.py`:

```python
from textual.widgets import OptionList

from brainfm_tui.app import BrainFmApp
from brainfm_tui.session import Activity


class FakeBackend:
    def __init__(self):
        self.actions: list[str] = []
        self.closed = False

    def list_activities(self):
        return [
            Activity("focus", "Focus", "dw", "Deep Work"),
            Activity("sleep", "Sleep", "nap", "Power Nap"),
        ]

    def play(self, activity: Activity) -> str:
        self.actions.append(f"play:{activity.activity_id}")
        return "Deep Work"

    def toggle(self) -> None:
        self.actions.append("toggle")

    def skip(self) -> str:
        self.actions.append("skip")
        return "next"

    def close(self) -> None:
        self.closed = True


async def test_lists_activities_and_enter_plays():
    backend = FakeBackend()
    app = BrainFmApp(backend)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        listed = pilot.app.query_one(OptionList)
        assert listed.option_count == 2
        await pilot.press("enter")
        await pilot.press("space")
        await pilot.press("n")
    assert backend.actions == ["play:dw", "toggle", "skip"]
    assert backend.closed is True
```

Do not bind Enter on the App. `OptionList` already emits selection on Enter. An App-level Enter binding with `priority=True` fights that. Space and `n` are App bindings with `priority=True` because OptionList does not use them.

```bash
uv run pytest tests/test_app.py -v
```

Expected: fail, `brainfm_tui.app` missing. Red.

Write `brainfm_tui/app.py`:

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from brainfm_tui.session import Activity


class BrainFmApp(App):
    TITLE = "Brain.fm"
    CSS = """
    Screen { align: center middle; }
    #now { height: 3; content-align: center middle; text-align: center; text-style: bold; }
    OptionList { height: 1fr; width: 60; }
    """
    BINDINGS = [
        Binding("space", "toggle", "Pause", priority=True),
        Binding("n", "skip", "Next", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, backend=None):
        super().__init__()
        self.backend = backend
        self._activities: list[Activity] = []
        self._playing = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("No track yet", id="now")
        yield OptionList()
        yield Footer()

    def on_mount(self) -> None:
        if self.backend is None:
            return
        try:
            self._activities = list(self.backend.list_activities())
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        listed = self.query_one(OptionList)
        for activity in self._activities:
            listed.add_option(Option(activity.label, id=activity.activity_id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        activity = next((item for item in self._activities if item.activity_id == event.option.id), None)
        if activity is None or self.backend is None:
            return
        try:
            name = self.backend.play(activity)
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._playing = True
        self.query_one("#now", Static).update(f"▶  {name}")

    def action_toggle(self) -> None:
        if self.backend is None:
            return
        self.backend.toggle()
        self._playing = not self._playing
        current = str(self.query_one("#now", Static).renderable)
        mark = "▶" if self._playing else "⏸"
        rest = current.split("  ", 1)[-1]
        self.query_one("#now", Static).update(f"{mark}  {rest}")

    def action_skip(self) -> None:
        if self.backend is None:
            return
        try:
            name = self.backend.skip()
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._playing = True
        self.query_one("#now", Static).update(f"▶  {name or 'next'}")

    def action_quit(self) -> None:
        if self.backend is not None:
            self.backend.close()
        self.exit()


def main() -> None:
    from brainfm_tui.runtime import Runtime

    BrainFmApp(Runtime()).run()
```

`runtime.py` does not exist yet. Tests inject `FakeBackend`, so they do not import it. Do not create it in this task.

```bash
uv run pytest tests/test_app.py -q
```

Expected: `1 passed`. Then:

```bash
uv run pytest -q
```

Expected: `12 passed`.

```bash
git add tests/test_app.py brainfm_tui/app.py
git commit -m "List activities in Textual"
```

### 7. Runtime wires API to mpv

Write `brainfm_tui/runtime.py`:

```python
from brainfm_tui.api import activities_for, catalog, next_serving, start_session, users_me
from brainfm_tui.player import Mpv
from brainfm_tui.session import Activity, load_token, track_id, track_name, track_url


class Runtime:
    def __init__(self):
        self.token = ""
        self.user_id = ""
        self.mpv = Mpv()
        self.current_id = ""
        self.current_name = ""

    def list_activities(self) -> list[Activity]:
        self.token = load_token()
        me = users_me(self.token)
        user = me.get("user") or {}
        self.user_id = str(user.get("id") or "")
        membership = me.get("membership") or {}
        if not membership.get("isActive"):
            raise RuntimeError("Brain.fm membership is not active")
        if not self.user_id:
            raise RuntimeError("users/me returned no user id")
        return catalog(self.token)

    def play(self, activity: Activity) -> str:
        result = start_session(self.token, self.user_id, activity.activity_id)
        servings = result.get("servings") or []
        if not servings:
            raise RuntimeError("session returned no servings")
        self._play_item(servings[0], fallback=activity.name)
        return self.current_name

    def toggle(self) -> None:
        self.mpv.toggle()

    def skip(self) -> str:
        if not self.current_id:
            raise RuntimeError("nothing playing")
        result = next_serving(self.token, self.user_id, self.current_id)
        servings = result.get("servings") or []
        if not servings:
            raise RuntimeError("no next serving")
        self._play_item(servings[0], fallback=self.current_name)
        return self.current_name

    def close(self) -> None:
        self.mpv.close()

    def _play_item(self, item: dict, fallback: str) -> None:
        url = track_url(item)
        self.current_id = track_id(item)
        self.current_name = track_name(item) or fallback
        self.mpv.load(url)
```

`activities_for` is imported and unused. Delete that import before committing. Do not leave it.

No unit test launches this class. It talks to the network and to mpv. Task 8 is the test.

```bash
uv run pytest -q
```

Expected: `12 passed`.

```bash
git add brainfm_tui/runtime.py
git commit -m "Connect the session, the API, and mpv"
```

### 8. Manual smoke

Do not print the token. If a command would, stop and delete that print before running it.

```bash
cd /home/kang/PARA/3_Resources/Apps/brain-fm-tui
uv run python - << 'PY'
from brainfm_tui.runtime import Runtime
rt = Runtime()
items = rt.list_activities()
print(f"user_id_len={len(rt.user_id)} activities={len(items)}")
print("first=", items[0].label if items else "NONE")
PY
```

Expected: `user_id_len=` a positive integer, `activities=` a positive integer, and a `first=` line like `Focus  ·  Deep Work`. The exact label depends on the account. `NONE` or a traceback is a failure.

- `AuthExpired` / `session expired`: open `https://my.brain.fm`, log in, quit that window, rerun this command. Do not add a password prompt.
- `GET https://api.brain.fm/v3/mentalStates/dynamic -> 404`: the version is wrong. Change `mental_states` and `activities_for` to `V2` and rerun. Do not change the session POST off v3 unless that POST also 404s. Record the status code in the commit message.
- `membership is not active`: stop. Do not hunt for another endpoint.

Then:

```bash
uv run brain-fm-tui
```

Expected, at the keyboard:

- The option list shows the same activities the probe printed.
- Enter on the first row starts sound within 5 seconds. The header line starts with `▶`.
- space pauses. space again resumes. The glyph flips.
- `n` changes the track without leaving a second mpv. Check with:

```bash
pgrep -a mpv
```

Expected while the TUI is still open: one `mpv` line, and that line contains `--input-ipc-server=` and `brain-fm-tui`. Not two.

- `q` exits. Then:

```bash
pgrep -a mpv || echo 'no leftover mpv'
```

Expected: `no leftover mpv`. If a pid remains, `kill` that pid only.

While playing, PipeWire should show mpv, not `brain-fm`:

```bash
wpctl status | rg -n 'mpv'
```

Expected: one mpv client line.

### 9. Launcher symlink

```bash
mkdir -p /home/kang/.local/bin
ln -sfn /home/kang/PARA/3_Resources/Apps/brain-fm-tui/.venv/bin/brain-fm-tui /home/kang/.local/bin/brain-fm-tui
command -v brain-fm-tui
```

Expected: `/home/kang/.local/bin/brain-fm-tui`

Do not commit the symlink.

Write `README.md` and commit it:

```markdown
# brain-fm-tui

Plays your Brain.fm subscription through mpv. No browser window.

The session is the JWT in WebKit localStorage (`persist:auth`), not the
cookie file. If the TUI says the session expired, open https://my.brain.fm
once and log in again.

```sh
uv run brain-fm-tui
```

Enter plays the highlighted station. Space pauses. n skips. q quits mpv too.
```

```bash
git add README.md
git commit -m "Document session source and keys"
```

## Tests / validation

```bash
cd /home/kang/PARA/3_Resources/Apps/brain-fm-tui
uv run pytest -q
```

Expected: `12 passed`.

Pytest green is not done. Done is task 8: one mpv process, sound, pause, skip, and no leftover mpv after `q`.

## Risks, tradeoffs, and open questions

- The cookie named `token` is a different JWT from `persist:auth`. Using it will 401 or authorize the wrong session. That is why this plan does not read the cookie file, even though that was the first guess.
- The JWT expires. Refresh is "open my.brain.fm once". There is no login form. Do not add one.
- `tokenedUrl` is a capability. Logging it is logging a credential. The TUI shows the track name only.
- If `mentalStates/dynamic` on v3 404s, task 8 says switch that one call to v2. Do not rewrite the client into a version negotiator.
- If a serving has neither `tokenedUrl` nor `url`, `track_url` raises. Print the serving's keys (not values) and extend `track_url` to the key that is actually a URL. Do not scrape the website.
- mpv IPC `cycle pause` is the pause implementation. If space does nothing, the socket path in `pgrep -a mpv` does not match `Mpv.sock`. Fix the path. Do not spawn a second player.
- No MPRIS. Desktop media keys will not control this. Add that only if asked.
- The AUR app can stay installed. This program never starts it. Two players at once means two streams on one subscription; pause the other one before judging the smoke test.
