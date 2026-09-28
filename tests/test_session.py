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
