from pathlib import Path
from narrator.config import load_settings, load_pronunciation

ROOT = Path(__file__).resolve().parents[1]

def test_load_settings_parses_nested_keys():
    s = load_settings(ROOT / "config/settings.yaml")
    assert s.engine == "chatterbox"
    assert s.seed == 12345
    assert s.cfg == 0.3
    assert s.max_chars == 250
    assert s.pause_inter_ms == 600
    assert s.loud_i == -18
    assert s.qa_max_wer == 0.15
    assert s.mp3_dir == Path("out")
    assert s.stories_dir == Path("stories")

def test_load_pronunciation_returns_compiled_pairs():
    p = load_pronunciation(ROOT / "config/pronunciation.yaml")
    assert p.respellings["Siobhan"] == "Shiv-awn"
    # replacements is a list of (pattern, replace) tuples; abbreviation patterns
    # (St./No./Mr./Mrs.) are handled upstream by expand_abbreviations, so the
    # config no longer duplicates them here.
    assert isinstance(p.replacements, list)
    assert all("Saint" not in rep for _, rep in p.replacements)

def test_invalid_engine_rejected(tmp_path):
    import pytest, yaml
    bad = tmp_path / "s.yaml"
    bad.write_text("engine: nope\n")
    with pytest.raises(ValueError):
        load_settings(bad)
