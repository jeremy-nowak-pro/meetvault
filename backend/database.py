import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./plaud.db")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_meetings(conn)

    # Populate client_id from project.client_id for existing meetings
    async with SessionLocal() as session:
        await session.execute(text("""
            UPDATE meetings
            SET client_id = (
                SELECT projects.client_id FROM projects WHERE projects.id = meetings.project_id
            )
            WHERE client_id IS NULL AND project_id IS NOT NULL
        """))
        await session.commit()


async def _migrate_meetings(conn):
    # Check if project_id still has a NOT NULL constraint (old schema)
    result = await conn.execute(text("PRAGMA table_info(meetings)"))
    cols = result.fetchall()
    project_id_col = next((c for c in cols if c[1] == 'project_id'), None)
    if not project_id_col or project_id_col[3] == 0:
        return  # Already nullable, nothing to do

    has_client_id = any(c[1] == 'client_id' for c in cols)
    client_id_select = "client_id" if has_client_id else "NULL"

    await conn.execute(text("""
        CREATE TABLE meetings_new (
            id INTEGER NOT NULL PRIMARY KEY,
            client_id INTEGER REFERENCES clients(id),
            project_id INTEGER REFERENCES projects(id),
            title VARCHAR(200),
            recorded_at DATETIME NOT NULL,
            duration_seconds INTEGER,
            audio_path VARCHAR(500),
            status VARCHAR(50) NOT NULL,
            transcript_raw TEXT,
            transcript_diarized TEXT,
            analysis TEXT,
            speakers TEXT,
            error_message TEXT,
            created_at DATETIME NOT NULL
        )
    """))
    await conn.execute(text(f"""
        INSERT INTO meetings_new
        SELECT id, {client_id_select}, project_id, title, recorded_at,
               duration_seconds, audio_path, status, transcript_raw,
               transcript_diarized, analysis, speakers, error_message, created_at
        FROM meetings
    """))
    await conn.execute(text("DROP TABLE meetings"))
    await conn.execute(text("ALTER TABLE meetings_new RENAME TO meetings"))
