"""FastAPIアプリケーションのエントリポイント。"""
from fastapi import FastAPI

from app.routers import maintenance_records, motorcycles

app = FastAPI(
    title="Chain Maintenance App",
    description="バイクのチェーンメンテナンス記録・計算API",
    version="0.1.0",
)

app.include_router(motorcycles.router)
app.include_router(maintenance_records.router)


@app.get("/health")
def health_check():
    """ヘルスチェック。ALBやECSのヘルスチェック用。"""
    return {"status": "ok"}