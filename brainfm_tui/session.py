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
