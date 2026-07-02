import hashlib, re
from pathlib import Path
from .audio import write_wav, read_wav

def cache_key(text: str, engine_param_id: str, ref_id: str, seed: int) -> str:
    raw = f"{engine_param_id}\x1f{ref_id}\x1f{seed}\x1f{text}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def _tokens(s: str) -> list:
    return re.findall(r"[a-z0-9']+", s.lower())

def word_error_rate(ref: str, hyp: str) -> float:
    r, h = _tokens(ref), _tokens(hyp)
    if not r:
        return 0.0 if not h else 1.0
    dp = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len(h) + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j-1] + 1, prev + (r[i-1] != h[j-1]))
            prev = cur
    return dp[len(h)] / len(r)

def ref_identity(ref) -> str:
    """Cache identity for a reference: path + size + mtime so that replacing
    the reference file at the same path invalidates stale cache entries.
    Falls back to the path string if the file is missing."""
    try:
        st = ref.wav_path.stat()
        return f"{ref.wav_path}:{st.st_size}:{st.st_mtime_ns}"
    except OSError:
        return f"{ref.wav_path}"

def generate_story(chunks, engine, ref, settings, cache_dir, transcriber=None) -> list:
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    ref_id = ref_identity(ref)
    out_paths = []
    for ch in chunks:
        key = cache_key(ch.text, engine.param_id, ref_id, settings.seed)
        dest = cache_dir / f"{ch.index:04d}_{key}.wav"
        if dest.exists():
            out_paths.append(dest); continue
        best_path, best_wer = None, 1e9
        attempts = settings.qa_max_retries + 1 if (settings.qa_enabled and transcriber) else 1
        tmp_paths = []
        for attempt in range(attempts):
            clip = engine.synthesize(ch.text, ref, seed=settings.seed + attempt)
            if not (settings.qa_enabled and transcriber):
                write_wav(dest, clip.samples, clip.sample_rate)
                best_path = dest; break
            tmp = dest.with_stem(f"{dest.stem}_a{attempt}")
            write_wav(tmp, clip.samples, clip.sample_rate)
            tmp_paths.append(tmp)
            wer = word_error_rate(ch.text, transcriber.transcribe(tmp))
            if wer < best_wer:
                best_path, best_wer = tmp, wer
            if wer <= settings.qa_max_wer:
                break
        # Move best take to dest; remove the rest
        if best_path is not None and best_path != dest:
            import shutil
            shutil.copy2(best_path, dest)
        for tmp in tmp_paths:
            if tmp != best_path and tmp.exists():
                tmp.unlink()
        if best_path in tmp_paths and best_path.exists() and best_path != dest:
            best_path.unlink()
        out_paths.append(dest)
    return out_paths
