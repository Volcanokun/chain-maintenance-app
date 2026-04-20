"""Alembic環境設定。

アプリ側の設定(app.core.config)とモデル定義(app.models)を読み込み、
--autogenerateでスキーマ差分を検出できるようにする。
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# アプリ側のモジュール読み込み
from app.core.config import settings
from app.db.base import Base
from app.models import MaintenanceRecord, Motorcycle  # noqa: F401  モデル登録のため必要

# Alembic設定オブジェクト
config = context.config

# .envのDATABASE_URLをAlembic設定に注入
config.set_main_option("sqlalchemy.url", settings.database_url)

# ロガー設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --autogenerateが参照するメタデータ。全モデルはBase経由で登録される。
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """オフラインモード(SQL文だけ生成、DBに接続しない)でのマイグレーション。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite対応: ALTER TABLE制限回避
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモード(DB接続してマイグレーション実行)。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite対応: ALTER TABLE制限回避
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()