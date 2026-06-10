import json
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.models import Meeting, Project, Client

router = APIRouter(prefix="/api/meetings", tags=["meetings"])

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage/audio")


@router.get("")
async def list_meetings(project_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    query = select(Meeting).order_by(Meeting.recorded_at.desc())
    if project_id:
        query = query.where(Meeting.project_id == project_id)
    result = await db.execute(query)
    meetings = result.scalars().all()
    return [
        {
            "id": m.id,
            "project_id": m.project_id,
            "title": m.title,
            "recorded_at": m.recorded_at,
            "duration_seconds": m.duration_seconds,
            "status": m.status,
        }
        for m in meetings
    ]


@router.post("/upload")
async def upload_meeting(
    background_tasks: BackgroundTasks,
    client_id: int = Form(...),
    title: Optional[str] = Form(None),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    from backend.models import Client
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    os.makedirs(STORAGE_DIR, exist_ok=True)
    uid = str(uuid.uuid4())
    raw_path = os.path.normpath(os.path.join(STORAGE_DIR, f"{uid}_raw{os.path.splitext(audio.filename)[1]}"))
    audio_path = os.path.normpath(os.path.join(STORAGE_DIR, f"{uid}.wav"))

    with open(raw_path, "wb") as f:
        content = await audio.read()
        f.write(content)

    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw_path, "-ar", "16000", "-ac", "1", audio_path],
        check=True, capture_output=True,
    )
    os.remove(raw_path)

    meeting = Meeting(
        client_id=client_id,
        title=title or f"RDV {datetime.now().strftime('%d/%m/%Y')}",
        audio_path=audio_path,
        status="uploaded",
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    background_tasks.add_task(run_pipeline, meeting.id)
    return {"id": meeting.id, "status": "processing"}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: int, db: AsyncSession = Depends(get_db)):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="RDV introuvable")

    analysis = json.loads(meeting.analysis) if meeting.analysis else None
    speakers = json.loads(meeting.speakers) if meeting.speakers else {}
    transcript = json.loads(meeting.transcript_diarized) if meeting.transcript_diarized else []

    return {
        "id": meeting.id,
        "client_id": meeting.client_id,
        "title": meeting.title,
        "recorded_at": meeting.recorded_at,
        "duration_seconds": meeting.duration_seconds,
        "status": meeting.status,
        "error_message": meeting.error_message,
        "speakers": speakers,
        "transcript": transcript,
        "analysis": analysis,
    }


@router.patch("/{meeting_id}/speakers")
async def update_speakers(meeting_id: int, speakers: dict, db: AsyncSession = Depends(get_db)):
    """Permet de renommer les locuteurs : {"SPEAKER_00": "Jérémy", "SPEAKER_01": "Client"}"""
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="RDV introuvable")
    meeting.speakers = json.dumps(speakers, ensure_ascii=False)
    await db.commit()
    return {"ok": True}


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: int, db: AsyncSession = Depends(get_db)):
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="RDV introuvable")
    if meeting.audio_path and os.path.exists(meeting.audio_path):
        os.remove(meeting.audio_path)
    await db.delete(meeting)
    await db.commit()
    return {"ok": True}


@router.post("/{meeting_id}/reanalyze")
async def reanalyze(meeting_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Relance uniquement l'analyse Ollama (utile après renommage des locuteurs)"""
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="RDV introuvable")
    if not meeting.transcript_diarized:
        raise HTTPException(status_code=400, detail="Transcription manquante")
    background_tasks.add_task(run_analysis_only, meeting_id)
    return {"ok": True, "status": "analyzing"}


@router.get("/{meeting_id}/export", response_class=PlainTextResponse)
async def export_meeting(meeting_id: int, db: AsyncSession = Depends(get_db)):
    from backend.pipeline.exporter import meeting_to_markdown
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="RDV introuvable")

    client = await db.get(Client, meeting.client_id) if meeting.client_id else None
    project = await db.get(Project, meeting.project_id) if meeting.project_id else None

    meeting_dict = {
        "id": meeting.id,
        "title": meeting.title,
        "recorded_at": meeting.recorded_at.isoformat(),
        "duration_seconds": meeting.duration_seconds,
        "status": meeting.status,
        "speakers": json.loads(meeting.speakers) if meeting.speakers else {},
        "transcript": json.loads(meeting.transcript_diarized) if meeting.transcript_diarized else [],
        "analysis": json.loads(meeting.analysis) if meeting.analysis else {},
    }

    md = meeting_to_markdown(
        meeting_dict,
        client_name=client.name if client else "Client",
        project_name=project.name if project else "Projet",
    )
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


async def run_pipeline(meeting_id: int):
    from backend.pipeline.transcriber import transcribe
    from backend.pipeline.diarizer import diarize
    from backend.pipeline.analyzer import analyze
    from backend.pipeline.notifier import send_push_notification
    from backend.database import SessionLocal

    async with SessionLocal() as db:
        meeting = await db.get(Meeting, meeting_id)
        try:
            # 1. Transcription
            meeting.status = "transcribing"
            await db.commit()
            transcript, duration = await transcribe(meeting.audio_path)
            meeting.transcript_raw = json.dumps(transcript, ensure_ascii=False)
            meeting.duration_seconds = int(duration)

            # 2. Diarisation
            meeting.status = "diarizing"
            await db.commit()
            diarized = await diarize(meeting.audio_path, transcript)
            meeting.transcript_diarized = json.dumps(diarized, ensure_ascii=False)

            # 3. Analyse
            meeting.status = "analyzing"
            await db.commit()
            analysis = await analyze(diarized, meeting.speakers)
            meeting.analysis = json.dumps(analysis, ensure_ascii=False)

            meeting.status = "done"
        except Exception as e:
            meeting.status = "error"
            meeting.error_message = str(e)
        finally:
            await db.commit()
            if meeting.status == "done":
                await send_push_notification(db, "Mímir", f"Analyse de « {meeting.title} » terminée")
            elif meeting.status == "error":
                await send_push_notification(db, "Mímir", f"Erreur lors du traitement de « {meeting.title} »")


async def run_analysis_only(meeting_id: int):
    from backend.pipeline.analyzer import analyze
    from backend.pipeline.notifier import send_push_notification
    from backend.database import SessionLocal

    async with SessionLocal() as db:
        meeting = await db.get(Meeting, meeting_id)
        try:
            meeting.status = "analyzing"
            await db.commit()
            diarized = json.loads(meeting.transcript_diarized)
            analysis = await analyze(diarized, meeting.speakers)
            meeting.analysis = json.dumps(analysis, ensure_ascii=False)
            meeting.status = "done"
        except Exception as e:
            meeting.status = "error"
            meeting.error_message = str(e)
        finally:
            await db.commit()
            if meeting.status == "done":
                await send_push_notification(db, "Mímir", f"Analyse de « {meeting.title} » terminée")
            elif meeting.status == "error":
                await send_push_notification(db, "Mímir", f"Erreur lors du traitement de « {meeting.title} »")

