from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from backend.database import get_db
from backend.models import DeviceToken

router = APIRouter(prefix="/api/devices", tags=["devices"])


class PushTokenPayload(BaseModel):
    token: str


@router.post("/push-token")
async def register_push_token(payload: PushTokenPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeviceToken).where(DeviceToken.token == payload.token))
    existing = result.scalar_one_or_none()
    if not existing:
        db.add(DeviceToken(token=payload.token))
        await db.commit()
    return {"ok": True}


@router.delete("/push-token")
async def delete_push_token(payload: PushTokenPayload, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(DeviceToken).where(DeviceToken.token == payload.token))
    await db.commit()
    return {"ok": True}
