from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from brainfm_tui.session import Activity


class BrainFmApp(App):
    TITLE = "Brain.fm"
    CSS = """
    Screen { align: center middle; }
    #now { height: 3; content-align: center middle; text-align: center; text-style: bold; }
    OptionList { height: 1fr; width: 60; }
    """
    BINDINGS = [
        Binding("space", "toggle", "Pause", priority=True),
        Binding("n", "skip", "Next", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, backend=None):
        super().__init__()
        self.backend = backend
        self._activities: list[Activity] = []
        self._playing = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("No track yet", id="now")
        yield OptionList()
        yield Footer()

    def on_mount(self) -> None:
        if self.backend is None:
            return
        try:
            self._activities = list(self.backend.list_activities())
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        listed = self.query_one(OptionList)
        for activity in self._activities:
            listed.add_option(Option(activity.label, id=activity.activity_id))
        listed.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        activity = next((item for item in self._activities if item.activity_id == event.option.id), None)
        if activity is None or self.backend is None:
            return
        try:
            name = self.backend.play(activity)
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._playing = True
        self.query_one("#now", Static).update(f"▶  {name}")

    def action_toggle(self) -> None:
        if self.backend is None:
            return
        self.backend.toggle()
        self._playing = not self._playing
        current = str(self.query_one("#now", Static).content)
        mark = "▶" if self._playing else "⏸"
        rest = current.split("  ", 1)[-1]
        self.query_one("#now", Static).update(f"{mark}  {rest}")

    def action_skip(self) -> None:
        if self.backend is None:
            return
        try:
            name = self.backend.skip()
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._playing = True
        self.query_one("#now", Static).update(f"▶  {name or 'next'}")

    def on_unmount(self) -> None:
        if self.backend is not None:
            self.backend.close()

    def action_quit(self) -> None:
        if self.backend is not None:
            self.backend.close()
        self.exit()


def main() -> None:
    from brainfm_tui.runtime import Runtime

    BrainFmApp(Runtime()).run()
