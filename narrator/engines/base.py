from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass
class Reference:
    wav_path: Path
    transcript: "str | None"

@dataclass
class AudioClip:
    samples: np.ndarray   # float32 mono, range [-1, 1]
    sample_rate: int

class TTSEngine(ABC):
    @property
    @abstractmethod
    def param_id(self) -> str: ...
    @abstractmethod
    def synthesize(self, text: str, ref: Reference, *, seed: int) -> AudioClip: ...
