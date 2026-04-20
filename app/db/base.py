"""SQLAlchemyの宣言ベース。全モデルの共通親クラス。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全テーブルモデルが継承する基底クラス。

    SQLAlchemy 2.0スタイルの宣言的マッピング。
    Alembicがこのクラスのサブクラスを検出してマイグレーションを生成する。
    """

    pass
