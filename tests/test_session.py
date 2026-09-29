import json

from brainfm_tui.session import Activity, track_id, track_url


def test_setup_saves_the_paste_and_nothing_else(tmp_path, capsys):
    from brainfm_tui.session import best_token, setup

    path = tmp_path / "session"
    token = _jwt(9_000)
    setup(path, read=lambda _prompt: f"  {token}\n")
    assert path.read_text().strip() == token
    assert path.stat().st_mode & 0o777 == 0o600
    assert best_token(path) == token
    assert token not in capsys.readouterr().out
    import getpass
    from brainfm_tui.session import setup as setup_fn

    assert setup_fn.__defaults__[-1] is getpass.getpass


def test_package_does_not_touch_the_desktop_app():
    root = __import__("pathlib").Path(__file__).parents[1] / "brainfm_tui"
    banned = ("fm.brain.desktop", "/usr/bin/brain-fm", "xdg-open", "persist:auth")
    for path in root.rglob("*.py"):
        text = path.read_text()
        for item in banned:
            assert item not in text, f"{path.name} contains {item}"


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


def test_now_playing_uses_title_genre_and_length():
    from brainfm_tui.session import format_now, now_playing

    item = {
        "track": {
            "name": "Light Bends",
            "beatsPerMinute": 85,
            "mentalState": {"displayValue": "Focus"},
            "webActivity": {"displayValue": "Deep Work"},
            "tags": [{"type": "genre", "value": "Lofi"}, {"type": "mood", "value": "Calm"}],
        },
        "trackVariation": {"lengthInSeconds": 1800, "tokenedUrl": "https://audio.brain.fm/x"},
    }
    now = now_playing(item)
    assert now.title == "Light Bends"
    assert now.activity == "Deep Work"
    assert now.mental_state == "Focus"
    assert now.genre == "Lofi"
    assert now.length_s == 1800
    assert now.bpm == 85
    text = format_now(now, playing=True)
    assert "Light Bends" in text
    assert "Lofi" in text
    assert "30 min" in text
    assert text.startswith("▶")


def test_best_token_reads_only_our_file(tmp_path):
    from brainfm_tui.session import best_token

    path = tmp_path / "session"
    path.write_text(_jwt(9_000) + "\n")
    assert best_token(path) == path.read_text().strip()
    missing = tmp_path / "missing"
    try:
        best_token(missing)
    except ValueError as exc:
        assert "setup" in str(exc)
    else:
        raise AssertionError("expected no session")


def test_refresh_does_not_launch_brain_fm(monkeypatch):
    import brainfm_tui.runtime as runtime

    assert not hasattr(runtime, "open_login")
    monkeypatch.setattr(runtime, "best_token", lambda: (_ for _ in ()).throw(ValueError("no session on disk")))
    player = runtime.Runtime()
    try:
        player.refresh_session()
    except ValueError as exc:
        assert "brain-fm" not in str(exc)
        assert "window" not in str(exc)
    else:
        raise AssertionError("expected no session")


def _jwt(exp: int) -> str:
    import base64
    body = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    head = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    return f"{head}.{body}.sig"


def test_adhd_is_high_only_and_levels_toggle():
    from brainfm_tui.session import adhd_on, format_mix, levels_from, toggle_adhd, toggle_nel

    assert adhd_on(["High"]) is True
    assert adhd_on(["Low", "High"]) is False
    assert toggle_adhd([]) == ["High"]
    assert toggle_adhd(["High"]) == []
    assert toggle_nel(["High"], "Low") == ["Low", "High"]
    assert toggle_nel(["Low", "Medium"], "Low") == ["Medium"]
    text = format_mix(["High"])
    assert "ADHD on" in text
    assert "● High" in text
    assert "○ Low" in text
    assert levels_from({"focus": {"neuralEffectLevels": ["High", "nope"]}}) == {"focus": ["High"]}


def test_activities_from_payload():
    from brainfm_tui.session import activities_from

    payload = [
        {"id": "focus", "displayValue": "Focus", "activities": [
            {"id": "dw", "displayValue": "Deep Work"},
        ]},
    ]
    assert activities_from(payload) == [Activity("focus", "Focus", "dw", "Deep Work")]
