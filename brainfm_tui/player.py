import json
import socket
import subprocess
import threading
import time
from pathlib import Path

SOCK = Path.home() / ".local/share/brain-fm-tui/mpv.sock"


def mpv_argv(sock: str, url: str) -> list[str]:
    return [
        "mpv",
        "--no-video",
        "--really-quiet",
        "--no-terminal",
        "--idle=yes",
        f"--input-ipc-server={sock}",
        url,
    ]


def track_ended(event: dict) -> bool:
    return event.get("event") == "end-file" and event.get("reason") == "eof"


def ipc_payload(command: list) -> bytes:
    return json.dumps({"command": command}).encode() + b"\n"


class Mpv:
    def __init__(self, sock: Path = SOCK):
        self.sock = sock
        self.proc: subprocess.Popen | None = None
        self._volume: float | None = None
        self._on_eof = None
        self._gen = 0

    def start(self, url: str) -> None:
        self.sock.parent.mkdir(parents=True, exist_ok=True)
        if self.sock.exists():
            self.sock.unlink()
        self.proc = subprocess.Popen(mpv_argv(str(self.sock), url))
        self._gen += 1
        threading.Thread(target=self._listen, args=(self._gen,), daemon=True).start()

    def watch(self, callback) -> None:
        self._on_eof = callback

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

    def _listen(self, gen: int) -> None:
        # ponytail: one extra socket. loadfile replace ends with reason=stop, so only eof advances.
        deadline = time.time() + 2
        client = None
        while time.time() < deadline and self._gen == gen:
            try:
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.settimeout(0.5)
                client.connect(str(self.sock))
                break
            except OSError:
                if client is not None:
                    client.close()
                client = None
                time.sleep(0.05)
        if client is None:
            return
        buf = b""
        try:
            while self._gen == gen:
                try:
                    chunk = client.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    self._handle(line, gen)
        finally:
            client.close()

    def _handle(self, line: bytes, gen: int) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return
        if self._gen == gen and track_ended(event) and self._on_eof is not None:
            self._on_eof()

    def close(self) -> None:
        self._gen += 1
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
