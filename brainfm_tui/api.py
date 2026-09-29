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
            raise AuthExpired("session expired") from exc
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


def start_session(token: str, user_id: str, activity_id: str, levels: list[str] | None = None, opener=urllib.request.urlopen) -> dict:
    body = {"dynamicActivityId": activity_id, "version": 3}
    if levels:
        body["neuralEffectLevels"] = levels
    return get_json(
        "POST",
        f"{V3}/users/{user_id}/sessions?platform=web",
        token,
        body=body,
        opener=opener,
    )


def session_preferences(token: str, user_id: str, opener=urllib.request.urlopen) -> dict:
    return get_json("GET", f"{V2}/users/{user_id}/session/preferences", token, opener=opener)


def set_neural_levels(token: str, user_id: str, mental_state: str, want: list[str], have: list[str], opener=urllib.request.urlopen) -> None:
    url = f"{V2}/users/{user_id}/session/preferences"
    remove = [item for item in have if item not in want]
    add = [item for item in want if item not in have]
    if remove:
        get_json("DELETE", url, token, body={"mentalState": mental_state, "neuralEffectLevels": remove}, opener=opener)
    if add:
        get_json("POST", url, token, body={"mentalState": mental_state, "neuralEffectLevels": add}, opener=opener)


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
