"""maintenance_recordsテーブルのモデル定義。"""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MaintenanceRecord(Base):
    """メンテナンス実施記録。

    motorcyclesに対してN:1の関係。
    performed_atはメンテ実施日(日付のみ)、created_atはレコード登録時刻。
    """

    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    motorcycle_id: Mapped[int] = mapped_column(
        ForeignKey("motorcycles.id", ondelete="CASCADE"),
        nullable=False,
    )
    performed_at: Mapped[date] = mapped_column(Date, nullable=False)
    odometer_km: Mapped[int] = mapped_column(Integer, nullable=False)
    lubricant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    motorcycle: Mapped["Motorcycle"] = relationship(back_populates="maintenance_records")  # noqa: F821

    __table_args__ = (
        CheckConstraint("odometer_km >= 0", name="ck_maintenance_records_odometer_nonneg"),
        # 複合インデックス(schema.mdで宣言したもの)
        Index(
            "idx_maintenance_records_motorcycle_performed",
            "motorcycle_id",
            "performed_at",
        ),
    )
