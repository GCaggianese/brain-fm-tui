from brainfm_tui.api import catalog, next_serving, start_session, users_me
from brainfm_tui.player import Mpv
from brainfm_tui.session import Activity, load_token, track_id, track_name, track_url


class Runtime:
    def __init__(self):
        self.token = ""
        self.user_id = ""
        self.mpv = Mpv()
        self.current_id = ""
        self.current_name = ""

    def list_activities(self) -> list[Activity]:
        self.token = load_token()
        me = users_me(self.token)
        user = me.get("user") or {}
        self.user_id = str(user.get("id") or "")
        membership = me.get("membership") or {}
        if not membership.get("isActive"):
            raise RuntimeError("Brain.fm membership is not active")
        if not self.user_id:
            raise RuntimeError("users/me returned no user id")
        return catalog(self.token)

    def play(self, activity: Activity) -> str:
        result = start_session(self.token, self.user_id, activity.activity_id)
        servings = result.get("servings") or []
        if not servings:
            raise RuntimeError("session returned no servings")
        self._play_item(servings[0], fallback=activity.name)
        return self.current_name

    def toggle(self) -> None:
        self.mpv.toggle()

    def skip(self) -> str:
        if not self.current_id:
            raise RuntimeError("nothing playing")
        result = next_serving(self.token, self.user_id, self.current_id)
        servings = result.get("servings") or []
        if not servings:
            raise RuntimeError("no next serving")
        self._play_item(servings[0], fallback=self.current_name)
        return self.current_name

    def close(self) -> None:
        self.mpv.close()

    def _play_item(self, item: dict, fallback: str) -> None:
        url = track_url(item)
        self.current_id = track_id(item)
        self.current_name = track_name(item) or fallback
        self.mpv.load(url)
