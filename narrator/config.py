from dataclasses import dataclass
from pathlib import Path
import yaml

VALID_ENGINES = {"chatterbox", "qwen", "fake"}

@dataclass
class Settings:
    engine: str; device: str; seed: int
    cfg: float; exaggeration: float
    ref_wav: Path; ref_transcript: Path
    stories_dir: Path
    max_chars: int
    pause_intra_ms: int; pause_inter_ms: int
    loud_i: float; loud_tp: float; loud_lra: float
    qa_enabled: bool; whisper_model: str; qa_max_retries: int; qa_max_wer: float
    speak_title: bool; speak_subtitle: bool
    mp3_dir: Path; m4b_path: Path

@dataclass
class Pronunciation:
    respellings: dict
    replacements: list  # list[tuple[pattern:str, replace:str]]

def load_settings(path: Path) -> Settings:
    d = yaml.safe_load(Path(path).read_text()) or {}
    engine = d.get("engine")
    if engine not in VALID_ENGINES:
        raise ValueError(f"engine must be one of {VALID_ENGINES}, got {engine!r}")
    seed = int(d.get("seed", 0))
    if seed == 0:
        raise ValueError("settings.yaml: seed must be a non-zero integer")
    cb = d.get("chatterbox", {}); ref = d.get("reference", {})
    ch = d.get("chunking", {}); pa = d.get("pauses_ms", {})
    lo = d.get("loudness", {}); qa = d.get("qa", {}); out = d.get("output", {})
    return Settings(
        engine=engine, device=d.get("device", "cuda"), seed=seed,
        cfg=float(cb.get("cfg", 0.3)), exaggeration=float(cb.get("exaggeration", 0.5)),
        ref_wav=Path(ref.get("path", "reference/ref.wav")),
        ref_transcript=Path(ref.get("transcript", "reference/ref.txt")),
        stories_dir=Path(d.get("stories_dir", "stories")),
        max_chars=int(ch.get("max_chars", 250)),
        pause_intra_ms=int(pa.get("intra_paragraph", 350)),
        pause_inter_ms=int(pa.get("inter_paragraph", 600)),
        loud_i=float(lo.get("i", -18)), loud_tp=float(lo.get("tp", -3)), loud_lra=float(lo.get("lra", 11)),
        qa_enabled=bool(qa.get("enabled", True)), whisper_model=qa.get("whisper_model", "small.en"),
        qa_max_retries=int(qa.get("max_retries", 3)), qa_max_wer=float(qa.get("max_word_error_rate", 0.15)),
        speak_title=bool(d.get("speak_title", True)), speak_subtitle=bool(d.get("speak_subtitle", False)),
        mp3_dir=Path(out.get("mp3_dir", "out")), m4b_path=Path(out.get("m4b_path", "out/audiobook.m4b")),
    )

def load_pronunciation(path: Path) -> Pronunciation:
    d = yaml.safe_load(Path(path).read_text()) or {}
    repl = [(r["pattern"], r["replace"]) for r in d.get("replacements", [])]
    return Pronunciation(respellings=dict(d.get("respellings", {})), replacements=repl)
