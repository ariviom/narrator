import json, subprocess
import numpy as np
import pytest
from pathlib import Path
from narrator.chunk import Chunk
from narrator.audio import write_wav
from narrator.stitch import assemble_story, loudnorm_pass1_cmd, build_m4b
from narrator.config import load_settings

ROOT = Path(__file__).resolve().parents[1]

def test_assemble_inserts_inter_paragraph_silence(tmp_path):
    s = load_settings(ROOT / "config/settings.yaml")
    sr = 24000
    p0 = tmp_path / "a.wav"; p1 = tmp_path / "b.wav"
    write_wav(p0, np.ones(sr, dtype=np.float32), sr)   # 1s
    write_wav(p1, np.ones(sr, dtype=np.float32), sr)   # 1s
    chunks = [Chunk("x", 0, 0, True), Chunk("y", 1, 1, True)]  # new paragraph at clip 2
    out, osr = assemble_story([p0, p1], chunks, s)
    expected = sr + int(sr * s.pause_inter_ms / 1000) + sr
    assert osr == sr and len(out) == expected

def test_loudnorm_pass1_cmd_has_targets():
    s = load_settings(ROOT / "config/settings.yaml")
    cmd = loudnorm_pass1_cmd(Path("in.wav"), s)
    joined = " ".join(cmd)
    assert "loudnorm" in joined and "I=-18" in joined and "TP=-3" in joined
    assert "print_format=json" in joined


@pytest.mark.integration
def test_build_m4b_chapters(tmp_path):
    sr = 24000
    w1 = tmp_path / "a.wav"; w2 = tmp_path / "b.wav"
    write_wav(w1, np.ones(sr // 2, dtype=np.float32) * 0.1, sr)   # 0.5s
    write_wav(w2, np.ones(sr, dtype=np.float32) * 0.1, sr)        # 1.0s
    out = tmp_path / "out.m4b"
    build_m4b([w1, w2], ["Chapter A", "Chapter B"], out)
    assert out.exists() and out.stat().st_size > 0
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_chapters", str(out)],
        capture_output=True, text=True, check=True)
    chapters = json.loads(res.stdout)["chapters"]
    assert len(chapters) == 2
    titles = [c["tags"]["title"] for c in chapters]
    assert titles == ["Chapter A", "Chapter B"]
