import numpy as np
from .base import TTSEngine, Reference, AudioClip

class FakeEngine(TTSEngine):
    def __init__(self, sr: int = 24000):
        self.sr = sr
    @property
    def param_id(self) -> str:
        return "fake"
    def synthesize(self, text: str, ref: Reference, *, seed: int) -> AudioClip:
        n = int(self.sr * (0.3 + 0.05 * len(text)))   # deterministic length
        return AudioClip(np.zeros(n, dtype=np.float32), self.sr)
