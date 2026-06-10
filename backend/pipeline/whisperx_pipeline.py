import os
import asyncio
import gc


HF_TOKEN = os.getenv("HF_TOKEN", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
DEVICE = "cuda"
COMPUTE_TYPE = "float16"


def _run_sync(audio_path: str):
    import torch
    import whisperx

    audio = whisperx.load_audio(audio_path)

    # 1. Transcription
    model = whisperx.load_model(WHISPER_MODEL, DEVICE, compute_type=COMPUTE_TYPE)
    result = model.transcribe(audio, batch_size=16, language="fr")
    del model
    gc.collect()
    torch.cuda.empty_cache()

    # 2. Alignement mot par mot
    model_a, metadata = whisperx.load_align_model(language_code="fr", device=DEVICE)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device=DEVICE)
    del model_a
    gc.collect()
    torch.cuda.empty_cache()

    # 3. Diarisation
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=HF_TOKEN, device=DEVICE)
    diarize_segments = diarize_model(audio)

    # 4. Attribution des speakers au niveau des mots
    result = whisperx.assign_word_speakers(diarize_segments, result)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
            "speaker": seg.get("speaker", "SPEAKER_00"),
        })

    duration = segments[-1]["end"] if segments else 0
    return segments, duration


async def transcribe_and_diarize(audio_path: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_sync, audio_path)
