from pathlib import Path
from narrator.reference import build_clip_cmd

def test_build_clip_cmd_is_mono_24k():
    cmd = build_clip_cmd(Path("audiobook.m4b"), "22:30", "22:45", Path("reference/ref.wav"))
    assert cmd[0] == "ffmpeg"
    assert "-ac" in cmd and cmd[cmd.index("-ac") + 1] == "1"
    assert "-ar" in cmd and cmd[cmd.index("-ar") + 1] == "24000"
    assert cmd[-1] == "reference/ref.wav"
    assert "-ss" in cmd and cmd[cmd.index("-ss") + 1] == "22:30"
    assert "-to" in cmd and cmd[cmd.index("-to") + 1] == "22:45"
