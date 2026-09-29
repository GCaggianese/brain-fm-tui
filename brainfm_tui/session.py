import json
import base64
import getpass
from dataclasses import dataclass
from pathlib import Path

SESSION = Path.home() / ".local/share/brain-fm-tui/session"
AUDIO_BASE = "https://audio.brain.fm/"
NELS = ("Low", "Medium", "High")


@dataclass(frozen=True)
class Activity:
    mental_state_id: str
    mental_state: str
    activity_id: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.mental_state}  ·  {self.name}"


def save_token(token: str, path: Path = SESSION) -> None:
    token = token.strip()
    if token.count(".") != 2 or any(ch.isspace() for ch in token):
        raise ValueError("that is not a token")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + "\n")
    path.chmod(0o600)


def setup(path: Path = SESSION, read=getpass.getpass) -> None:
    save_token(read("paste your cookie here: "), path)
    print("saved")


def best_token(path: Path = SESSION) -> str:
    try:
        token = path.read_text().strip()
    except OSError:
        token = ""
    if token.count(".") != 2:
        raise ValueError("no session on disk; run brain-fm-tui --setup")
    return token


def token_exp(token: str) -> float:
    if not token or token.count(".") != 2:
        return 0.0
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        body = json.loads(base64.urlsafe_b64decode(payload))
        return float(body.get("exp") or 0)
    except (ValueError, json.JSONDecodeError):
        return 0.0


def token_fresh(token: str, now: float) -> bool:
    return token_exp(token) > now + 15


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
    return now_playing(item).title


@dataclass(frozen=True)
class NowPlaying:
    title: str
    activity: str = ""
    mental_state: str = ""
    length_s: int = 0
    bpm: int = 0
    genre: str = ""


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _tag(track: dict, kind: str) -> str:
    for tag in track.get("tags") or []:
        if isinstance(tag, dict) and tag.get("type") == kind and tag.get("value"):
            return str(tag["value"])
    return ""


def now_playing(item: dict, fallback: Activity | None = None) -> NowPlaying:
    serving = _serving(item)
    track = serving.get("track") or {}
    variation = serving.get("trackVariation") or {}
    activity = ""
    for key in ("webActivity", "mobileActivity"):
        block = track.get(key) or {}
        if isinstance(block, dict) and block.get("displayValue"):
            activity = str(block["displayValue"])
            break
    mental = track.get("mentalState") or {}
    state = str(mental.get("displayValue") or "") if isinstance(mental, dict) else ""
    title = str(track.get("name") or track.get("title") or "")
    if fallback is not None:
        title = title or fallback.name
        activity = activity or fallback.name
        state = state or fallback.mental_state
    return NowPlaying(title, activity, state, _int(variation.get("lengthInSeconds")), _int(track.get("beatsPerMinute")), _tag(track, "genre"))


def format_now(now: NowPlaying | None, playing: bool) -> str:
    if now is None or not now.title:
        return "No track yet"
    lines = [f"{'▶' if playing else '⏸'}  {now.title}"]
    bits = [part for part in (now.mental_state, now.activity, now.genre) if part]
    extra = []
    if now.length_s:
        extra.append(f"{now.length_s // 60} min")
    if now.bpm:
        extra.append(f"{now.bpm} bpm")
    if bits:
        lines.append("  ·  ".join(bits))
    if extra:
        lines.append("  ·  ".join(extra))
    return "\n".join(lines)


def adhd_on(levels: list[str]) -> bool:
    return levels == ["High"]


def toggle_nel(levels: list[str], name: str) -> list[str]:
    chosen = set(levels)
    if name in chosen:
        chosen.remove(name)
    else:
        chosen.add(name)
    return [item for item in NELS if item in chosen]


def toggle_adhd(levels: list[str]) -> list[str]:
    return [] if adhd_on(levels) else ["High"]


def format_mix(levels: list[str]) -> str:
    parts = [f"{i} {'●' if name in levels else '○'} {name}" for i, name in enumerate(NELS, start=1)]
    return f"a ADHD {'on' if adhd_on(levels) else 'off'}    " + "   ".join(parts)


def levels_from(payload) -> dict[str, list[str]]:
    if not isinstance(payload, dict):
        return {}
    found = {}
    for key, value in payload.items():
        if not isinstance(value, dict):
            continue
        raw = value.get("neuralEffectLevels") or []
        found[str(key)] = [item for item in NELS if item in raw]
    return found


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
