import asyncio
import shutil

from textual.widgets import OptionList, Static, TabbedContent

from brainfm_tui.app import BrainFmApp
from brainfm_tui.session import Activity, NowPlaying


class FakeBackend:
    def __init__(self):
        self.actions: list[str] = []
        self.closed = False
        self.volume = None
        self.levels = {"focus": ["High"]}

    def list_activities(self):
        return [
            Activity("focus", "Focus", "dw", "Deep Work"),
            Activity("relax", "Relax", "chill", "Chill"),
            Activity("sleep", "Sleep", "nap", "Power Nap"),
            Activity("meditate", "Meditate", "breathe", "Breathe"),
        ]

    def play(self, activity: Activity) -> NowPlaying:
        self.actions.append(f"play:{activity.activity_id}")
        if activity.activity_id == "nap":
            return NowPlaying("Night Drift", "Power Nap", "Sleep", 1800, 60, "Ambient")
        return NowPlaying("In the Moment", "Deep Work", "Focus", 1800, 85, "Lofi")

    def toggle(self) -> None:
        self.actions.append("toggle")

    def skip(self) -> NowPlaying:
        self.actions.append("skip")
        return NowPlaying("Next Track", "Deep Work", "Focus", 900, 90, "Jazz")

    def set_volume(self, level: float) -> None:
        self.volume = level
        self.actions.append(f"vol:{level}")

    def close(self) -> None:
        self.closed = True

    def refresh_session(self):
        self.actions.append("refresh")
        return self.list_activities() + [Activity("focus", "Focus", "light", "Light Work")]

    def set_levels(self, state: str, levels: list[str]) -> None:
        self.actions.append(f"levels:{state}:{','.join(levels)}")
        self.levels[state] = list(levels)


def test_lists_activities_and_enter_plays():
    asyncio.run(_lists_activities_and_enter_plays())


async def _lists_activities_and_enter_plays():
    backend = FakeBackend()
    app = BrainFmApp(backend, mpris=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        listed = pilot.app.query_one("#list-focus", OptionList)
        assert listed.option_count == 1
        assert pilot.app.query_one("#list-sleep", OptionList).option_count == 1
        await pilot.press("enter")
        text = str(pilot.app.query_one("#now", Static).content)
        assert "In the Moment" in text
        assert "Lofi" in text
        assert "30 min" in text
        await pilot.press("space")
        await pilot.press("n")
        text = str(pilot.app.query_one("#now", Static).content)
        assert "Next Track" in text
    assert backend.actions == ["play:dw", "toggle", "skip"]
    assert backend.closed is True


def test_tab_switches_category():
    asyncio.run(_tab_switches_category())


async def _tab_switches_category():
    backend = FakeBackend()
    app = BrainFmApp(backend, mpris=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await pilot.press("tab")
        await pilot.press("tab")
        tabs = pilot.app.query_one(TabbedContent)
        assert tabs.active == "sleep"
        await pilot.press("enter")
        text = str(pilot.app.query_one("#now", Static).content)
        assert "Night Drift" in text
        assert "Ambient" in text
        assert "30 min" in text
    assert backend.actions == ["play:nap"]


def test_ctrl_r_reloads_after_sign_in():
    asyncio.run(_ctrl_r_reloads_after_sign_in())


async def _ctrl_r_reloads_after_sign_in():
    backend = FakeBackend()
    app = BrainFmApp(backend, mpris=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await pilot.press("ctrl+r")
        for _ in range(20):
            await pilot.pause()
            if "refresh" in backend.actions:
                break
        assert pilot.app.query_one("#list-focus", OptionList).option_count == 2
    assert backend.actions == ["refresh"]


def test_adhd_and_nel_follow_the_visible_category():
    asyncio.run(_adhd_and_nel_follow_the_visible_category())


async def _adhd_and_nel_follow_the_visible_category():
    backend = FakeBackend()
    app = BrainFmApp(backend, mpris=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        mix = str(pilot.app.query_one("#mix", Static).content)
        assert "ADHD on" in mix
        await pilot.press("enter")
        await pilot.press("a")
        for _ in range(20):
            await pilot.pause()
            if any(item.startswith("levels:") for item in backend.actions):
                break
        mix = str(pilot.app.query_one("#mix", Static).content)
        assert "ADHD off" in mix
        assert backend.actions[-1] == "play:dw"
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.pause()
        await pilot.press("1")
        for _ in range(20):
            await pilot.pause()
            if "levels:sleep:Low" in backend.actions:
                break
        assert backend.levels["sleep"] == ["Low"]
        assert backend.levels["focus"] == []


async def _pc(*args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "playerctl", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode() or out.decode()
    return out.decode().strip()


def test_playerctl_controls_playback():
    if not shutil.which("playerctl"):
        return
    asyncio.run(_playerctl_controls_playback())


async def _playerctl_controls_playback():
    backend = FakeBackend()
    name = "brainfmtui_test"
    app = BrainFmApp(backend, mpris=True, mpris_name=name)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.app._mpris_ready.wait()
        await pilot.press("enter")
        await pilot.pause()
        assert await _pc("-p", name, "metadata", "xesam:title") == "In the Moment"
        await _pc("-p", name, "play-pause")
        await _pc("-p", name, "next")
        await pilot.pause()
        assert await _pc("-p", name, "metadata", "xesam:title") == "Next Track"
        await _pc("-p", name, "volume", "0.4")
    assert "toggle" in backend.actions
    assert "skip" in backend.actions
    assert backend.volume == 0.4
    assert backend.closed is True
