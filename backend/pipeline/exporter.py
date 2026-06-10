import json
from datetime import datetime
from typing import Optional


def _fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def _fmt_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "Durée inconnue"
    m = seconds // 60
    return f"{m} min"


def meeting_to_markdown(meeting_data: dict, client_name: str, project_name: str) -> str:
    a = meeting_data.get("analysis") or {}
    speakers = meeting_data.get("speakers") or {}
    transcript = meeting_data.get("transcript") or []
    recorded_at = meeting_data.get("recorded_at", "")

    if isinstance(recorded_at, str):
        try:
            recorded_at = datetime.fromisoformat(recorded_at).strftime("%d/%m/%Y")
        except Exception:
            pass

    lines = [
        f"# {meeting_data.get('title', 'RDV')}",
        f"**Client :** {client_name} | **Projet :** {project_name}",
        f"**Date :** {recorded_at} | **Durée :** {_fmt_duration(meeting_data.get('duration_seconds'))}",
        "",
    ]

    if a.get("summary"):
        lines += ["## Résumé", a["summary"], ""]

    if a.get("client_requests"):
        lines.append("## Demandes client")
        for item in a["client_requests"]:
            checkbox = "- [x]" if item.get("done") else "- [ ]"
            lines.append(f"{checkbox} {item['text']}")
        lines.append("")

    if a.get("client_validations"):
        lines.append("## Validé par le client")
        for item in a["client_validations"]:
            lines.append(f"- ✅ {item['text']}")
        lines.append("")

    if a.get("questions_answers"):
        lines.append("## Questions / Réponses")
        for qa in a["questions_answers"]:
            answered = "✅" if qa.get("answered") else "⚠️ Non répondu"
            lines.append(f"- ❓ {qa['question']}")
            if qa.get("answer"):
                lines.append(f"  → {answered} {qa['answer']}")
            else:
                lines.append(f"  → {answered}")
        lines.append("")

    if a.get("jeremy_commitments"):
        lines.append("## Tes engagements")
        for item in a["jeremy_commitments"]:
            checkbox = "- [x]" if item.get("done") else "- [ ]"
            lines.append(f"{checkbox} {item['text']}")
        lines.append("")

    if a.get("pending_points"):
        lines.append("## Points en suspens")
        for item in a["pending_points"]:
            lines.append(f"- ⏳ {item['text']}")
        lines.append("")

    if a.get("next_step"):
        lines += ["## Prochaine étape", a["next_step"], ""]

    if transcript:
        lines.append("## Transcription complète")
        prev_speaker = None
        for seg in transcript:
            raw_speaker = seg.get("speaker", "SPEAKER_00")
            name = speakers.get(raw_speaker, raw_speaker.replace("SPEAKER_0", "Interlocuteur "))
            if name != prev_speaker:
                lines.append(f"\n**{name}** _{_fmt_time(seg['start'])}_")
                prev_speaker = name
            lines.append(seg["text"])

    return "\n".join(lines)
