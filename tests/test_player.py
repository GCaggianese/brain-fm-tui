from brainfm_tui.player import ipc_payload, mpv_argv


def test_mpv_argv_is_one_quiet_process():
    argv = mpv_argv("/tmp/brainfm-mpv.sock", "https://audio.brain.fm/x")
    assert argv[0] == "mpv"
    assert "--no-video" in argv
    assert "--input-ipc-server=/tmp/brainfm-mpv.sock" in argv
    assert argv[-1] == "https://audio.brain.fm/x"


def test_ipc_payload_is_one_json_line():
    raw = ipc_payload(["loadfile", "https://audio.brain.fm/x", "replace"])
    assert raw.endswith(b"\n")
    assert b"loadfile" in raw
