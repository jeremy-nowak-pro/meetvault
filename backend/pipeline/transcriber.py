import os
import asyncio
from typing import Tuple

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        model_name = os.getenv("WHISPER_MODEL", "large-v3")
        # GPU si disponible, sinon CPU
        _model = WhisperModel(model_name, device="cuda", compute_type="float16")
    return _model


def _transcribe_sync(audio_path: str) -> Tuple[list, float]:
    model = _get_model()
    segments, info = model.transcribe(
        audio_path,
        language="fr",
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,  # supprime les silences
    )

    result = []
    for seg in segments:
        result.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "words": [
                {"word": w.word, "start": round(w.start, 2), "end": round(w.end, 2)}
                for w in (seg.words or [])
            ],
        })

    return result, info.duration


async def transcribe(audio_path: str) -> Tuple[list, float]:
    """Lance Whisper dans un thread pour ne pas bloquer l'event loop FastAPI."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, audio_path)
