"""motorcyclesテーブルのモデル定義。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Motorcycle(Base):
    """バイク情報。

    1ユーザーあたり原則1台だが、構造上は複数対応可能。
    スプロケ丁数・チェーンコマ数・タイヤ円周はチェーン計算の基礎値。
    """

    __tablename__ = "motorcycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    front_sprocket: Mapped[int] = mapped_column(Integer, nullable=False)
    rear_sprocket: Mapped[int] = mapped_column(Integer, nullable=False)
    chain_links: Mapped[int] = mapped_column(Integer, nullable=False)
    tire_circumference_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),  # UPDATE時に自動で現在時刻をセット
    )

    # N:1の逆方向リレーション定義。
    # maintenance_records側からのアクセスと双方向になる。
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(  # noqa: F821
        back_populates="motorcycle",
        cascade="all, delete-orphan",
    )

    # CHECK制約。SQLAlchemyのテーブル引数として定義する。
    __table_args__ = (
        CheckConstraint("front_sprocket > 0", name="ck_motorcycles_front_sprocket_positive"),
        CheckConstraint("rear_sprocket > 0", name="ck_motorcycles_rear_sprocket_positive"),
        CheckConstraint("chain_links > 0", name="ck_motorcycles_chain_links_positive"),
        CheckConstraint(
            "tire_circumference_mm > 0", name="ck_motorcycles_tire_circumference_positive"
        ),
    )
