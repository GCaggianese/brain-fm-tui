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
