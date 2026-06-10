import os
import json
import asyncio
from typing import Optional


SYSTEM_PROMPT = """Tu es un assistant spécialisé dans l'analyse de réunions commerciales pour un développeur freelance.
Tu reçois la transcription d'un rendez-vous client et tu dois en extraire les informations structurées suivantes.

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans commentaire, sans texte autour.

Structure JSON attendue :
{
  "client_requests": [
    {"text": "Description de la demande", "done": false}
  ],
  "client_validations": [
    {"text": "Ce que le client a validé ou accepté"}
  ],
  "questions_answers": [
    {
      "question": "Question posée par le client",
      "answer": "Réponse donnée",
      "answered": true
    }
  ],
  "jeremy_commitments": [
    {"text": "Engagement pris par Jérémy", "done": false}
  ],
  "pending_points": [
    {"text": "Point en suspens ou à confirmer"}
  ],
  "next_step": "Description de la prochaine étape suggérée",
  "summary": "Résumé en 2-3 phrases du RDV"
}

Règles importantes :
- "answered": false si la question a été esquivée ou si la réponse n'est pas claire
- Sois précis et factuel, ne invente rien qui n'est pas dans la transcription
- Si un élément n'existe pas, retourne un tableau vide []
- Textes en français
"""


def _format_transcript(diarized: list, speakers_map: Optional[str]) -> str:
    """Convertit la transcription diarisée en texte lisible pour le LLM."""
    speakers = {}
    if speakers_map:
        try:
            speakers = json.loads(speakers_map)
        except Exception:
            pass

    lines = []
    for seg in diarized:
        raw_speaker = seg.get("speaker", "SPEAKER_00")
        name = speakers.get(raw_speaker, raw_speaker.replace("SPEAKER_0", "Interlocuteur "))
        lines.append(f"[{_fmt_time(seg['start'])}] {name}: {seg['text']}")

    return "\n".join(lines)


def _fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _analyze_sync(diarized: list, speakers_map: Optional[str]) -> dict:
    import ollama

    model = os.getenv("OLLAMA_MODEL", "mistral")
    transcript_text = _format_transcript(diarized, speakers_map)

    user_message = f"""Voici la transcription du rendez-vous client :

{transcript_text}

Analyse cette transcription et retourne le JSON structuré demandé."""

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        format="json",
        options={"temperature": 0.1},
    )

    raw = response["message"]["content"].strip()

    # Extraire le bloc JSON même si le LLM a ajouté du texte autour
    import re
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        raw = match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Retourne une structure vide plutôt que de crasher
        return {
            "client_requests": [],
            "client_validations": [],
            "questions_answers": [],
            "jeremy_commitments": [],
            "pending_points": [],
            "next_step": "",
            "summary": "Analyse incomplète — le modèle n'a pas retourné un JSON valide. Relance l'analyse.",
        }


async def analyze(diarized: list, speakers_map: Optional[str] = None) -> dict:
    """Lance l'analyse Ollama dans un thread."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _analyze_sync, diarized, speakers_map)
