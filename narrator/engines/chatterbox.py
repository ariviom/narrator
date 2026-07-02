# NOTE (2026-06-20): Chatterbox adapter — kwargs must be verified against PyPI/repo at build time.
# Verified against chatterbox-tts <VERSION> on <DATE>:
#   ChatterboxTTS.from_pretrained(device=...) ; model.generate(text, audio_prompt_path=...) -> torch tensor ; model.sr
# At install time, confirm:
#   - https://pypi.org/project/chatterbox-tts/  (latest version, requires-python)
#   - https://github.com/resemble-ai/chatterbox  (ChatterboxTTS.from_pretrained / .generate signature, model.sr)
# Adapt cfg_weight / exaggeration kwarg names if the API has changed.
import numpy as np
from .base import TTSEngine, Reference, AudioClip

class ChatterboxEngine(TTSEngine):
    def __init__(self, device: str = "cuda", cfg: float = 0.3, exaggeration: float = 0.5):
        from chatterbox.tts import ChatterboxTTS
        import torch
        self._torch = torch
        # Determinism is best-effort: seeding plus cudnn deterministic mode does
        # not fully pin GPU TTS output, but reduces run-to-run variance.
        torch.backends.cudnn.deterministic = True
        self.model = ChatterboxTTS.from_pretrained(device=device)
        self.cfg = cfg; self.exaggeration = exaggeration
        self.sr = int(self.model.sr)
    @property
    def param_id(self) -> str:
        return f"chatterbox:cfg={self.cfg}:exag={self.exaggeration}"
    def synthesize(self, text: str, ref: Reference, *, seed: int) -> AudioClip:
        # Best-effort determinism: seed CPU and (if present) all CUDA devices.
        self._torch.manual_seed(seed)
        if self._torch.cuda.is_available():
            self._torch.cuda.manual_seed_all(seed)
        wav = self.model.generate(
            text, audio_prompt_path=str(ref.wav_path),
            cfg_weight=self.cfg, exaggeration=self.exaggeration,
        )  # NOTE: confirm kwarg names at build time; adapt if different
        samples = wav.squeeze().detach().cpu().numpy().astype(np.float32)
        return AudioClip(samples, self.sr)
