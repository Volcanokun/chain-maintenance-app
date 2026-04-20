"""pytest共通フィクスチャ。

テスト用のインメモリSQLiteを毎テスト作成・破棄する。
本番DBに一切影響しない。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# テスト用インメモリSQLite
SQLITE_TEST_URL = "sqlite:///file::memory:?cache=shared&uri=true"
engine_test = create_engine(SQLITE_TEST_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=engine_test, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def setup_db():
    """各テスト前にテーブル作成、テスト後に全テーブル削除。"""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture()
def db_session(setup_db):
    """テスト用DBセッション。"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(setup_db):
    """テスト用HTTPクライアント。

    FastAPIのDIをオーバーライドし、テスト用DBセッションを注入する。
    """

    def _override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
