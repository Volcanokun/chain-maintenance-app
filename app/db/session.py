"""DB接続エンジンとセッション管理。"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite用の接続引数
# check_same_thread=False: SQLiteは同一スレッド制限があるが、FastAPIでは
# 複数スレッドから触る可能性があるので無効化する
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,  # Trueにすると発行SQLがログ出力される(デバッグ時に便利)
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI依存性注入用のDBセッション取得関数。

    エンドポイント関数で Depends(get_db) として使う。
    リクエスト終了時に自動的にセッションを閉じる。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()