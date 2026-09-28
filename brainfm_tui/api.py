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
