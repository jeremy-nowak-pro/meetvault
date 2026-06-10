import os
import asyncio
import json
from typing import Optional

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        import huggingface_hub
        from pyannote.audio import Pipeline
        import torch
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise RuntimeError("HF_TOKEN manquant dans .env — requis pour pyannote")
        huggingface_hub.login(token=hf_token, add_to_git_credential=False)
        _pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        _pipeline.to(torch.device("cpu"))
    return _pipeline


def _diarize_sync(audio_path: str, transcript: list) -> list:
    """Fusionne la transcription Whisper avec la diarisation pyannote."""
    pipeline = _get_pipeline()
    diarization = pipeline(audio_path)

    # Construire une liste de segments (start, end, speaker)
    speaker_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
        })

    # Assigner un locuteur à chaque segment Whisper
    result = []
    for seg in transcript:
        seg_mid = (seg["start"] + seg["end"]) / 2
        speaker = _find_speaker(seg_mid, speaker_segments)
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "speaker": speaker,
            "text": seg["text"],
        })

    return result


def _find_speaker(timestamp: float, speaker_segments: list) -> str:
    """Trouve le locuteur qui parle au timestamp donné."""
    best = "SPEAKER_00"
    for seg in speaker_segments:
        if seg["start"] <= timestamp <= seg["end"]:
            return seg["speaker"]
    # Fallback : locuteur le plus proche
    if speaker_segments:
        closest = min(speaker_segments, key=lambda s: abs((s["start"] + s["end"]) / 2 - timestamp))
        best = closest["speaker"]
    return best


async def diarize(audio_path: str, transcript: list) -> list:
    """Lance pyannote dans un thread pour ne pas bloquer l'event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _diarize_sync, audio_path, transcript)
