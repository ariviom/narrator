import numpy as np, soundfile as sf
from pathlib import Path

def write_wav(path, samples, sr):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, sr)

def read_wav(path):
    data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1).astype("float32")
    return data, sr

def silence(ms, sr):
    return np.zeros(int(sr * ms / 1000), dtype=np.float32)
