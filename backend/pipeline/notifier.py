import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import DeviceToken


async def send_push_notification(db: AsyncSession, title: str, body: str):
    result = await db.execute(select(DeviceToken))
    tokens = result.scalars().all()
    if not tokens:
        return

    messages = [
        {"to": t.token, "title": title, "body": body, "sound": "default"}
        for t in tokens
    ]

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://exp.host/--/api/v2/push/send",
            json=messages,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
