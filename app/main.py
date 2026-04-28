"""FastAPIアプリケーションのエントリポイント。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import maintenance_records, motorcycles

app = FastAPI(
    title="Chain Maintenance App",
    description="バイクのチェーンメンテナンス記録・計算API",
    version="0.1.0",
)

app.include_router(motorcycles.router)
app.include_router(maintenance_records.router)

_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/health")
def health_check():
    """ヘルスチェック。ALBやECSのヘルスチェック用。"""
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")


@app.get("/records")
def records():
    return FileResponse(_STATIC / "records.html")
