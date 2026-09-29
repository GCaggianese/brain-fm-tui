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
        assert "session expired" in str(exc)
    else:
        raise AssertionError("expected AuthExpired")


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


def test_set_neural_levels_posts_adds_and_deletes_removals():
    from brainfm_tui.api import set_neural_levels, start_session

    seen = []

    def opener(req, timeout):
        seen.append((req.method, json.loads(req.data.decode())))
        return FakeResponse(200, {"result": {}})

    set_neural_levels("tok", "u1", "focus", ["High"], ["Low"], opener=opener)
    assert seen == [
        ("DELETE", {"mentalState": "focus", "neuralEffectLevels": ["Low"]}),
        ("POST", {"mentalState": "focus", "neuralEffectLevels": ["High"]}),
    ]
    seen.clear()

    def opener_session(req, timeout):
        seen.append(json.loads(req.data.decode()))
        return FakeResponse(200, {"result": {"servings": []}})

    start_session("tok", "u1", "dw", ["High"], opener=opener_session)
    assert seen[0]["neuralEffectLevels"] == ["High"]
    start_session("tok", "u1", "dw", [], opener=opener_session)
    assert "neuralEffectLevels" not in seen[1]
