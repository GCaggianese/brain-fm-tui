from brainfm_tui.runtime import Runtime
from brainfm_tui import runtime
from brainfm_tui.session import Activity


def _serving(name: str) -> dict:
    return {"track": {"id": name, "name": name}, "trackVariation": {"tokenedUrl": f"https://cdn.example/{name}"}}


def _runtime(batches: list[list[dict]]) -> tuple[Runtime, list[str], list[str]]:
    loaded: list[str] = []
    calls: list[str] = []

    class Quiet:
        def load(self, url: str) -> None:
            loaded.append(url)

    def start(token, user_id, activity_id, levels=None):
        calls.append("start")
        return {"servings": batches.pop(0)}

    runtime.start_session = start
    player = Runtime()
    player.token = "t"
    player.user_id = "u"
    player.mpv = Quiet()
    return player, loaded, calls


def test_skip_plays_the_next_queued_serving():
    player, loaded, calls = _runtime([[_serving("one"), _serving("two")]])
    player.play(Activity("focus", "Focus", "dw", "Deep Work"))
    player.skip()
    assert loaded == ["https://cdn.example/one", "https://cdn.example/two"]
    assert calls == ["start"]


def test_skip_refills_the_queue_from_the_same_session():
    player, loaded, calls = _runtime([[_serving("one")], [_serving("two")]])
    player.play(Activity("focus", "Focus", "dw", "Deep Work"))
    player.skip()
    assert loaded == ["https://cdn.example/one", "https://cdn.example/two"]
    assert calls == ["start", "start"]
