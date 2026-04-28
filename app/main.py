"""FastAPIアプリケーションのエントリポイント。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import bikes

app = FastAPI(
    title="Chain Maintenance App",
    description="バイクのチェーン計算リファレンス",
    version="0.2.0",
)

app.include_router(bikes.router)

_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")
