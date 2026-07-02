from pathlib import Path
from typing import Protocol

class Transcriber(Protocol):
    def transcribe(self, wav_path: Path) -> str: ...

class WhisperTranscriber:
    def __init__(self, model_name: str = "small.en", device: str = "cuda", compute_type: str | None = None):
        self.model_name = model_name
        self.device = device
        # Pick a sensible compute type per device when not specified.
        self.compute_type = compute_type or ("float16" if device == "cuda" else "int8")
        self._model = None
    def _ensure(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
    def transcribe(self, wav_path: Path) -> str:
        self._ensure()
        segments, _ = self._model.transcribe(str(wav_path))
        return " ".join(s.text.strip() for s in segments).strip()
