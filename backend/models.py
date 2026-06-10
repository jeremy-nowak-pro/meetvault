from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped["Client"] = relationship(back_populates="projects")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Pipeline status
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    # uploaded → transcribing → diarizing → analyzing → done | error

    # Résultats pipeline
    transcript_raw: Mapped[Optional[str]] = mapped_column(Text)      # JSON segments Whisper
    transcript_diarized: Mapped[Optional[str]] = mapped_column(Text)  # JSON segments avec locuteur
    analysis: Mapped[Optional[str]] = mapped_column(Text)             # JSON analyse Ollama

    # Noms des locuteurs (assignés manuellement ou auto)
    speakers: Mapped[Optional[str]] = mapped_column(Text)  # JSON {"SPEAKER_00": "Jérémy", ...}

    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="meetings")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
