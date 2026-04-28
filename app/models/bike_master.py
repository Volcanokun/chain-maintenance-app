"""bike_masters テーブルのモデル定義。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BikeMaster(Base):
    __tablename__ = "bike_masters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    maker: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    displacement_cc: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    front_sprocket: Mapped[int] = mapped_column(Integer, nullable=False)
    rear_sprocket: Mapped[int] = mapped_column(Integer, nullable=False)
    chain_links: Mapped[int] = mapped_column(Integer, nullable=False)
    chain_pitch: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rear_tire_size: Mapped[str] = mapped_column(String(30), nullable=False)
