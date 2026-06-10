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
        # Add client_id column to existing databases that don't have it yet
        try:
            await conn.execute(text(
                "ALTER TABLE meetings ADD COLUMN client_id INTEGER REFERENCES clients(id)"
            ))
        except Exception:
            pass  # Column already exists

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
