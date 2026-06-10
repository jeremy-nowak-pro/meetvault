from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.models import Client, Project

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientCreate(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


@router.get("")
async def list_clients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).order_by(Client.name))
    clients = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "email": c.email,
            "created_at": c.created_at,
        }
        for c in clients
    ]


@router.post("")
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    client = Client(**data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return {"id": client.id, "name": client.name}


@router.get("/{client_id}/projects")
async def list_projects(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.client_id == client_id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [{"id": p.id, "name": p.name, "description": p.description, "created_at": p.created_at} for p in projects]


@router.post("/{client_id}/projects")
async def create_project(client_id: int, data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    project = Project(client_id=client_id, **data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return {"id": project.id, "name": project.name}


@router.delete("/{client_id}")
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    await db.delete(client)
    await db.commit()
    return {"ok": True}


@router.delete("/{client_id}/projects/{project_id}")
async def delete_project(client_id: int, project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project or project.client_id != client_id:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    await db.delete(project)
    await db.commit()
    return {"ok": True}
