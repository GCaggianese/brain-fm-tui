from dbus_next import NameFlag, RequestNameReply, Variant
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method

from brainfm_tui.session import NowPlaying

# ponytail: no seek, loop, or playlist. playerctl next calls our skip, not mpv.


def metadata_dict(now: NowPlaying | None, track_no: int) -> dict:
    title = now.title if now and now.title else "Brain.fm"
    album = now.activity if now else ""
    genre = [now.genre] if now and now.genre else []
    length = (now.length_s if now else 0) * 1_000_000
    return {
        "xesam:title": Variant("s", title),
        "xesam:artist": Variant("as", ["Brain.fm"]),
        "xesam:album": Variant("s", album),
        "xesam:genre": Variant("as", genre),
        "mpris:length": Variant("x", length),
        "mpris:trackid": Variant("o", f"/org/mpris/MediaPlayer2/track/{track_no}"),
    }


class Root(ServiceInterface):
    def __init__(self, app):
        super().__init__("org.mpris.MediaPlayer2")
        self.app = app

    @method()
    def Raise(self):
        return None

    @method()
    def Quit(self):
        self.app.action_quit()

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s":
        return "Brain.fm"

    @dbus_property(access=PropertyAccess.READ)
    def DesktopEntry(self) -> "s":
        return "brain-fm-tui"

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":
        return ["https"]

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":
        return ["audio/mpeg"]


class Player(ServiceInterface):
    def __init__(self, app):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self.app = app
        self._volume = 1.0

    def changed(self) -> None:
        self.emit_properties_changed({
            "PlaybackStatus": self.PlaybackStatus,
            "Metadata": self.Metadata,
        })

    @method()
    def Next(self):
        self.app.action_skip()

    @method()
    def Previous(self):
        return None

    @method()
    def Pause(self):
        if self.app._playing:
            self.app.action_toggle()

    @method()
    def PlayPause(self):
        self.app.action_toggle()

    @method()
    def Stop(self):
        if self.app._playing:
            self.app.action_toggle()

    @method()
    def Play(self):
        if not self.app._playing and self.app._now is not None:
            self.app.action_toggle()

    @method()
    def Seek(self, offset: "x"):
        return None

    @method()
    def SetPosition(self, track_id: "o", position: "x"):
        return None

    @method()
    def OpenUri(self, uri: "s"):
        return None

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":
        if self.app._now is None:
            return "Stopped"
        return "Playing" if self.app._playing else "Paused"

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        return metadata_dict(self.app._now, self.app._track_no)

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def LoopStatus(self) -> "s":
        return "None"

    @dbus_property(access=PropertyAccess.READ)
    def Rate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> "d":
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def Shuffle(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> "x":
        return 0

    @dbus_property()
    def Volume(self) -> "d":
        return self._volume

    @Volume.setter
    def Volume(self, value: "d"):
        self._volume = float(value)
        backend = self.app.backend
        if backend is not None and hasattr(backend, "set_volume"):
            backend.set_volume(self._volume)


async def publish(app, name: str = "brainfm"):
    bus = await MessageBus().connect()
    app._mpris = Player(app)
    bus.export("/org/mpris/MediaPlayer2", Root(app))
    bus.export("/org/mpris/MediaPlayer2", app._mpris)
    reply = await bus.request_name(
        f"org.mpris.MediaPlayer2.{name}",
        NameFlag.REPLACE_EXISTING | NameFlag.DO_NOT_QUEUE,
    )
    if reply not in (RequestNameReply.PRIMARY_OWNER, RequestNameReply.ALREADY_OWNER):
        name = "brainfmtui"
        await bus.request_name("org.mpris.MediaPlayer2.brainfmtui")
    app._mpris_name = name
    return bus
