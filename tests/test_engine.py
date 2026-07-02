import types
import numpy as np
from pathlib import Path
from narrator.engines.base import Reference, AudioClip, TTSEngine
from narrator.engines.fake import FakeEngine
from narrator.engines import load_engine

def test_fake_engine_is_a_ttsengine_and_deterministic():
    e = FakeEngine()
    assert isinstance(e, TTSEngine)
    r = Reference(Path("reference/ref.wav"), None)
    a = e.synthesize("hello world", r, seed=1)
    b = e.synthesize("hello world", r, seed=1)
    assert isinstance(a, AudioClip) and a.sample_rate == 24000
    assert np.array_equal(a.samples, b.samples)

def test_fake_engine_length_scales_with_text():
    e = FakeEngine()
    r = Reference(Path("x"), None)
    short = e.synthesize("hi", r, seed=1).samples
    long = e.synthesize("hi " * 50, r, seed=1).samples
    assert len(long) > len(short)

def test_param_id_stable():
    assert FakeEngine().param_id == "fake"

def test_load_engine_fake():
    settings = types.SimpleNamespace(engine="fake")
    engine = load_engine(settings)
    assert isinstance(engine, FakeEngine)
