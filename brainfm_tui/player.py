import json
import socket
import subprocess
from pathlib import Path

SOCK = Path.home() / ".local/share/brain-fm-tui/mpv.sock"


def mpv_argv(sock: str, url: str) -> list[str]:
    return [
        "mpv",
        "--no-video",
        "--really-quiet",
        "--no-terminal",
        f"--input-ipc-server={sock}",
        url,
    ]


def ipc_payload(command: list) -> bytes:
    return json.dumps({"command": command}).encode() + b"\n"


class Mpv:
    def __init__(self, sock: Path = SOCK):
        self.sock = sock
        self.proc: subprocess.Popen | None = None
        self._volume: float | None = None

    def start(self, url: str) -> None:
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        if self.sock.exists():
            self.sock.unlink()
        self.proc = subprocess.Popen(mpv_argv(str(self.sock), url))

    def _ipc(self, command: list) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect(str(self.sock))
            sock.sendall(ipc_payload(command))
            sock.recv(4096)

    def load(self, url: str) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self.start(url)
            return
        self._ipc(["loadfile", url, "replace"])
        self._ipc(["set_property", "pause", False])
        self._apply_volume()

    def set_volume(self, level: float) -> None:
        self._volume = max(0.0, min(1.0, level))
        self._apply_volume()

    def _apply_volume(self) -> None:
        if self._volume is None or self.proc is None or self.proc.poll() is not None:
            return
        self._ipc(["set_property", "volume", self._volume * 100])

    def toggle(self) -> None:
        self._ipc(["cycle", "pause"])

    def close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
