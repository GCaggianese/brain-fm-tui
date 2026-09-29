import time

from brainfm_tui.api import catalog, session_preferences, set_neural_levels, start_session, users_me
from brainfm_tui.player import Mpv
from brainfm_tui.session import (
    Activity,
    NowPlaying,
    best_token,
    levels_from,
    now_playing,
    token_fresh,
    track_url,
)


class Runtime:
    def __init__(self):
        self.token = ""
        self.user_id = ""
        self.mpv = Mpv()
        self.activity: Activity | None = None
        self.queue: list[dict] = []
        self.current = None
        self.levels: dict[str, list[str]] = {}

    def list_activities(self) -> list[Activity]:
        return self._load(best_token())

    def refresh_session(self) -> list[Activity]:
        token = best_token()
        if not token_fresh(token, time.time()):
            raise RuntimeError("session expired")
        return self._load(token)

    def _load(self, token: str) -> list[Activity]:
        self.token = token
        me = users_me(token)
        user = me.get("user") or {}
        self.user_id = str(user.get("id") or "")
        membership = me.get("membership") or {}
        if not membership.get("isActive"):
            raise RuntimeError("Brain.fm membership is not active")
        if not self.user_id:
            raise RuntimeError("users/me returned no user id")
        try:
            self.levels = levels_from(session_preferences(self.token, self.user_id))
        except Exception:
            self.levels = {}
        return catalog(self.token)

    def set_levels(self, mental_state: str, levels: list[str]) -> None:
        have = self.levels.get(mental_state, [])
        set_neural_levels(self.token, self.user_id, mental_state, levels, have)
        self.levels[mental_state] = list(levels)

    def play(self, activity: Activity) -> NowPlaying:
        self.activity = activity
        self.queue = self._servings()
        return self._play_item(self.queue.pop(0), activity)

    def toggle(self) -> None:
        self.mpv.toggle()

    def skip(self) -> NowPlaying:
        if not self.queue:
            self.queue = self._servings()
        return self._play_item(self.queue.pop(0), self.activity)

    def close(self) -> None:
        self.mpv.close()

    def set_volume(self, level: float) -> None:
        self.mpv.set_volume(level)

    def _play_item(self, item: dict, activity: Activity | None) -> NowPlaying:
        url = track_url(item)
        self.current = now_playing(item, activity)
        self.mpv.load(url)
        return self.current

    def _servings(self) -> list[dict]:
        if self.activity is None:
            raise RuntimeError("nothing playing")
        result = start_session(self.token, self.user_id, self.activity.activity_id, self.levels.get(self.activity.mental_state_id, []))
        servings = result.get("servings") or []
        if not servings:
            raise RuntimeError("session returned no servings")
        return servings
