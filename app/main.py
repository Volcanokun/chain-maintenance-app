"""FastAPIアプリケーションのエントリポイント。"""

import os
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

# ECS 環境でのみ X-Ray を有効化（XRAY_ENABLED=true が必要）
if os.getenv("XRAY_ENABLED", "false").lower() == "true":
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.ext.starlette.middleware import XRayMiddleware

    xray_recorder.configure(
        service="chain-maintenance-app",
        daemon_address="127.0.0.1:2000",
        context_missing="LOG_ERROR",
    )
    app.add_middleware(XRayMiddleware, recorder=xray_recorder)

app.include_router(bikes.router)

_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")
