import asyncio

from textual.widgets import OptionList

from brainfm_tui.app import BrainFmApp
from brainfm_tui.session import Activity


class FakeBackend:
    def __init__(self):
        self.actions: list[str] = []
        self.closed = False

    def list_activities(self):
        return [
            Activity("focus", "Focus", "dw", "Deep Work"),
            Activity("sleep", "Sleep", "nap", "Power Nap"),
        ]

    def play(self, activity: Activity) -> str:
        self.actions.append(f"play:{activity.activity_id}")
        return "Deep Work"

    def toggle(self) -> None:
        self.actions.append("toggle")

    def skip(self) -> str:
        self.actions.append("skip")
        return "next"

    def close(self) -> None:
        self.closed = True


def test_lists_activities_and_enter_plays():
    asyncio.run(_lists_activities_and_enter_plays())


async def _lists_activities_and_enter_plays():
    backend = FakeBackend()
    app = BrainFmApp(backend)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        listed = pilot.app.query_one(OptionList)
        assert listed.option_count == 2
        await pilot.press("enter")
        await pilot.press("space")
        await pilot.press("n")
    assert backend.actions == ["play:dw", "toggle", "skip"]
    assert backend.closed is True
