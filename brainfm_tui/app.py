import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, OptionList, Static, TabbedContent, TabPane
from textual.widgets.option_list import Option

from brainfm_tui.session import Activity, format_mix, format_now, toggle_adhd, toggle_nel

# ponytail: fixed 4 Brain.fm mental states. A fifth from the catalog is skipped until a pane is added.
CATEGORIES = ("Focus", "Relax", "Sleep", "Meditate")


class BrainFmApp(App):
    TITLE = "Brain.fm"
    CSS = """
    Screen { align: center middle; }
    #now { height: 5; width: 62; content-align: center middle; text-align: center; }
    #mix { height: 1; width: 62; content-align: center middle; text-align: center; }
    #cats { height: 1fr; width: 62; }
    OptionList { height: 1fr; }
    """
    BINDINGS = [
        Binding("tab", "next_category", "Category", priority=True),
        Binding("shift+tab", "prev_category", show=False, priority=True),
        Binding("space", "toggle", "Pause", priority=True),
        Binding("n", "skip", "Next", priority=True),
        Binding("a", "adhd", "ADHD", priority=True),
        Binding("1", "nel('Low')", show=False, priority=True),
        Binding("2", "nel('Medium')", show=False, priority=True),
        Binding("3", "nel('High')", show=False, priority=True),
        Binding("ctrl+r", "refresh_session", "Reload", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, backend=None, mpris: bool = True, mpris_name: str = "brainfm"):
        super().__init__()
        self.backend = backend
        self._mpris_enabled = mpris
        self._mpris_name = mpris_name
        self._mpris = None
        self._bus = None
        self._mpris_ready = asyncio.Event()
        self._activities: list[Activity] = []
        self._now = None
        self._playing = False
        self._track_no = 0
        self._activity: Activity | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("No track yet", id="now")
        yield Static("", id="mix")
        with TabbedContent(id="cats"):
            for name in CATEGORIES:
                with TabPane(name, id=name.lower()):
                    yield OptionList(id=f"list-{name.lower()}")
        yield Footer()

    def on_mount(self) -> None:
        if self.backend is not None and hasattr(self.backend, "watch_end"):
            self.backend.watch_end(lambda: self.call_from_thread(self.action_skip))
        self._fill()
        if self._mpris_enabled:
            self.run_worker(self._start_mpris(), exclusive=True)
        else:
            self._mpris_ready.set()

    async def _start_mpris(self) -> None:
        try:
            from brainfm_tui.mpris import publish

            wanted = self._mpris_name
            self._bus = await publish(self, wanted)
            if self._mpris_name != wanted:
                self.notify(f"playerctl: {self._mpris_name}", severity="warning")
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="warning")
        finally:
            self._mpris_ready.set()

    def _fill(self) -> None:
        if self.backend is None:
            return
        try:
            self._activities = list(self.backend.list_activities())
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._show_activities()
        self._paint_mix()

    def _show_activities(self) -> None:
        for name in CATEGORIES:
            self.query_one(f"#list-{name.lower()}", OptionList).clear_options()
        for activity in self._activities:
            try:
                listed = self.query_one(f"#list-{activity.mental_state.lower()}", OptionList)
            except Exception:
                continue
            listed.add_option(Option(activity.name, id=activity.activity_id))
        for name in CATEGORIES:
            listed = self.query_one(f"#list-{name.lower()}", OptionList)
            if listed.option_count:
                listed.highlighted = 0
        self.query_one("#list-focus", OptionList).focus()

    def _state(self) -> str:
        try:
            active = self.query_one(TabbedContent).active
        except Exception:
            return "focus"
        return active or "focus"

    def _levels(self) -> list[str]:
        stored = getattr(self.backend, "levels", None) or {}
        return list(stored.get(self._state(), []))

    def _paint_mix(self) -> None:
        self.query_one("#mix", Static).update(format_mix(self._levels()))

    def on_tabbed_content_tab_activated(self, _event) -> None:
        self._paint_mix()

    def action_adhd(self) -> None:
        self._commit(toggle_adhd(self._levels()))

    def action_nel(self, name: str) -> None:
        self._commit(toggle_nel(self._levels(), name))

    def _commit(self, levels: list[str]) -> None:
        backend = self.backend
        if backend is None or not hasattr(backend, "set_levels"):
            return
        self.run_worker(self._commit_levels(backend, self._state(), levels), exclusive=True, group="mix")

    async def _commit_levels(self, backend, state: str, levels: list[str]) -> None:
        try:
            await asyncio.to_thread(backend.set_levels, state, levels)
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._paint_mix()
        if self._activity is None or self._activity.mental_state_id != state or self._now is None:
            return
        try:
            self._now = await asyncio.to_thread(backend.play, self._activity)
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._playing = True
        self._track_no += 1
        self._show()

    def action_refresh_session(self) -> None:
        backend = self.backend
        if backend is None:
            return
        self.run_worker(self._refresh_session(backend), exclusive=True, group="refresh")

    async def _refresh_session(self, backend) -> None:
        try:
            items = await asyncio.to_thread(backend.refresh_session)
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._activities = list(items)
        self._show_activities()
        self.notify("Session refreshed")

    def _cycle(self, step: int) -> None:
        tabs = self.query_one(TabbedContent)
        ids = [name.lower() for name in CATEGORIES]
        cur = tabs.active if tabs.active in ids else ids[0]
        nxt = ids[(ids.index(cur) + step) % len(ids)]
        tabs.active = nxt
        self.query_one(f"#list-{nxt}", OptionList).focus()

    def action_next_category(self) -> None:
        self._cycle(1)

    def action_prev_category(self) -> None:
        self._cycle(-1)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        activity = next((item for item in self._activities if item.activity_id == event.option.id), None)
        if activity is None or self.backend is None:
            return
        try:
            self._now = self.backend.play(activity)
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._activity = activity
        self._playing = True
        self._track_no += 1
        self._show()

    def _show(self) -> None:
        self.query_one("#now", Static).update(format_now(self._now, self._playing))
        if self._mpris is not None:
            self._mpris.changed()

    def action_toggle(self) -> None:
        if self.backend is None or self._now is None:
            return
        self.backend.toggle()
        self._playing = not self._playing
        self._show()

    def action_skip(self) -> None:
        if self.backend is None:
            return
        try:
            self._now = self.backend.skip()
        except Exception as exc:
            self.notify(str(exc).splitlines()[0], severity="error")
            return
        self._playing = True
        self._track_no += 1
        self._show()

    def on_unmount(self) -> None:
        if self.backend is not None:
            self.backend.close()
        if self._bus is not None:
            self._bus.disconnect()

    def action_quit(self) -> None:
        if self.backend is not None:
            self.backend.close()
        self.exit()


def main() -> None:
    import sys

    if "--setup" in sys.argv:
        from brainfm_tui.session import setup

        try:
            setup()
        except ValueError as exc:
            print(exc, file=sys.stderr)
            raise SystemExit(1) from None
        return
    from brainfm_tui.runtime import Runtime

    BrainFmApp(Runtime()).run()
