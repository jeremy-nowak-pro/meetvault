import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.database import init_db
from backend.routers import clients, meetings, devices


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="plaud-local", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router)
app.include_router(meetings.router)
app.include_router(devices.router)

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def index():
    return FileResponse("frontend/index.html")


@app.get("/record")
async def record():
    return FileResponse("frontend/record.html")


@app.get("/meeting/{meeting_id}")
async def meeting_page(meeting_id: int):
    return FileResponse("frontend/meeting.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    cert = "desktop-788t5j3.tail72565e.ts.net.crt"
    key  = "desktop-788t5j3.tail72565e.ts.net.key"
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        ssl_certfile=cert,
        ssl_keyfile=key,
    )
