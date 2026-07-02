def load_engine(settings):
    if settings.engine == "fake":
        from .fake import FakeEngine
        return FakeEngine()
    if settings.engine == "chatterbox":
        from .chatterbox import ChatterboxEngine
        return ChatterboxEngine(device=settings.device, cfg=settings.cfg, exaggeration=settings.exaggeration)
    if settings.engine == "qwen":
        from .qwen import QwenEngine
        return QwenEngine(device=settings.device)
    raise ValueError(settings.engine)
