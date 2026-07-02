import pytest
from pathlib import Path
from narrator.generate import cache_key, word_error_rate, generate_story, ref_identity
from narrator.chunk import Chunk
from narrator.engines.fake import FakeEngine
from narrator.engines.base import Reference
from narrator.config import load_settings

ROOT = Path(__file__).resolve().parents[1]

def test_cache_key_stable_and_sensitive():
    a = cache_key("hello", "fake", "ref1", 1)
    assert a == cache_key("hello", "fake", "ref1", 1)
    assert a != cache_key("hello", "fake", "ref1", 2)
    assert a != cache_key("hello!", "fake", "ref1", 1)

def test_ref_identity_changes_with_file_content(tmp_path):
    import numpy as np
    from narrator.audio import write_wav
    ref_path = tmp_path / "ref.wav"
    write_wav(ref_path, np.zeros(8000, dtype=np.float32), 16000)
    id1 = ref_identity(Reference(ref_path, "t"))
    # Rewrite with different size -> identity (and thus cache key) must change.
    write_wav(ref_path, np.zeros(24000, dtype=np.float32), 16000)
    id2 = ref_identity(Reference(ref_path, "t"))
    assert id1 != id2
    assert cache_key("x", "fake", id1, 1) != cache_key("x", "fake", id2, 1)


def test_ref_identity_falls_back_to_path_when_missing(tmp_path):
    missing = tmp_path / "nope.wav"
    assert ref_identity(Reference(missing, None)) == str(missing)


def test_generate_story_rekeys_when_reference_file_changes(tmp_path):
    import numpy as np
    from narrator.audio import write_wav
    s = load_settings(ROOT / "config/settings.yaml")
    s.qa_enabled = False
    cache = tmp_path / "cache"
    ref_path = tmp_path / "ref.wav"
    chunks = [Chunk("one two", 0, 0, True)]
    eng = FakeEngine()

    write_wav(ref_path, np.zeros(8000, dtype=np.float32), 16000)
    p1 = generate_story(chunks, eng, Reference(ref_path, None), s, cache_dir=cache)[0]
    # Replace the reference at the same path with different content.
    write_wav(ref_path, np.zeros(24000, dtype=np.float32), 16000)
    p2 = generate_story(chunks, eng, Reference(ref_path, None), s, cache_dir=cache)[0]
    assert p1.name != p2.name, "stale cache must not be reused after ref changes"


def test_wer_perfect_and_mismatch():
    assert word_error_rate("the cat sat", "The cat sat.") == 0.0
    assert word_error_rate("a b c d", "a x c d") == 0.25

def test_generate_story_caches_and_is_idempotent(tmp_path):
    s = load_settings(ROOT / "config/settings.yaml")
    s.qa_enabled = False
    chunks = [Chunk("one two", 0, 0, True), Chunk("three four", 1, 0, False)]
    ref = Reference(Path("reference/ref.wav"), None)
    eng = FakeEngine()
    paths1 = generate_story(chunks, eng, ref, s, cache_dir=tmp_path)
    assert all(p.exists() for p in paths1) and len(paths1) == 2
    mtimes = [p.stat().st_mtime_ns for p in paths1]
    paths2 = generate_story(chunks, eng, ref, s, cache_dir=tmp_path)   # reuse, no rewrite
    assert [p.stat().st_mtime_ns for p in paths2] == mtimes

def test_qa_retries_until_match(tmp_path):
    s = load_settings(ROOT / "config/settings.yaml")
    s.qa_enabled = True; s.qa_max_wer = 0.0; s.qa_max_retries = 2
    calls = {"n": 0}
    class FlakyTranscriber:
        def transcribe(self, wav_path):
            calls["n"] += 1
            return "" if calls["n"] == 1 else "match"
    chunks = [Chunk("match", 0, 0, True)]
    paths = generate_story(chunks, FakeEngine(), Reference(Path("r"), None), s,
                           cache_dir=tmp_path, transcriber=FlakyTranscriber())
    assert calls["n"] >= 2 and paths[0].exists()


def test_qa_keeps_lowest_wer_take(tmp_path):
    """Lowest-WER take must be preserved even when a later attempt is worse."""
    import numpy as np
    from narrator.audio import read_wav
    from narrator.engines.base import TTSEngine, AudioClip

    # Engine that embeds a per-attempt fingerprint into the first sample.
    # WAV float32 clips to [-1, 1], so we use 0.25 for attempt 0 and 0.75 for attempt 1.
    FINGERPRINT = {0: 0.25, 1: 0.75}
    attempt_counter = {"n": 0}

    class SeededEngine(TTSEngine):
        @property
        def param_id(self): return "seeded"
        def synthesize(self, text, ref, *, seed):
            idx = seed - 10   # seed=10 → attempt 0, seed=11 → attempt 1
            samples = np.zeros(24000, dtype=np.float32)
            samples[0] = np.float32(FINGERPRINT.get(idx, 0.5))
            return AudioClip(samples, 24000)

    s = load_settings(ROOT / "config/settings.yaml")
    s.qa_enabled = True
    s.qa_max_wer = -1.0   # impossible threshold → no early exit; all attempts run
    s.qa_max_retries = 1  # exactly 2 attempts (attempt 0 and attempt 1)
    s.seed = 10

    # attempt 0 → transcriber returns "hello" → WER 0.0 (best, fingerprint 0.25)
    # attempt 1 → transcriber returns "zzz"   → WER 1.0 (worse, fingerprint 0.75)
    calls = {"n": 0}
    class TrackingTranscriber:
        def transcribe(self, wav_path):
            n = calls["n"]; calls["n"] += 1
            return "hello" if n == 0 else "zzz zzz zzz"

    chunks = [Chunk("hello", 0, 0, True)]
    paths = generate_story(chunks, SeededEngine(), Reference(Path("r"), None), s,
                           cache_dir=tmp_path, transcriber=TrackingTranscriber())
    assert calls["n"] == 2, "both attempts must run"
    final_samples, _ = read_wav(paths[0])
    # First sample encodes which attempt was kept. Attempt 0 (lower WER) → 0.25
    assert final_samples[0] == pytest.approx(0.25, abs=1e-3), (
        "generate_story must keep the lowest-WER take (attempt 0, fingerprint 0.25), "
        f"but got first-sample={final_samples[0]}"
    )
