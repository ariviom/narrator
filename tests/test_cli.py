from pathlib import Path
from narrator.cli import build_parser, resolve_story

def test_parser_has_subcommands():
    p = build_parser()
    ns = p.parse_args(["normalize", "--story", "12", "--dry-run"])
    assert ns.cmd == "normalize" and ns.story == "12" and ns.dry_run is True

def test_resolve_story_by_number_and_fragment(tmp_path):
    (tmp_path / "12_chapter-twelve").mkdir()
    (tmp_path / "02_chapter-two").mkdir()
    assert resolve_story("12", tmp_path).name.startswith("12_")
    assert resolve_story("twelve", tmp_path).name.endswith("chapter-twelve")
