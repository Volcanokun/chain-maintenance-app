"""motorcycles APIの入出力スキーマ。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MotorcycleCreate(BaseModel):
    """バイク新規登録時の入力。"""

    name: str = Field(..., min_length=1, max_length=100, examples=["MT-09 SP"])
    front_sprocket: int = Field(..., gt=0, examples=[16])
    rear_sprocket: int = Field(..., gt=0, examples=[45])
    chain_links: int = Field(..., gt=0, examples=[118])
    tire_circumference_mm: int = Field(..., gt=0, examples=[1992])


class MotorcycleUpdate(BaseModel):
    """バイク更新時の入力。全フィールド任意(部分更新対応)。"""

    name: str | None = Field(None, min_length=1, max_length=100)
    front_sprocket: int | None = Field(None, gt=0)
    rear_sprocket: int | None = Field(None, gt=0)
    chain_links: int | None = Field(None, gt=0)
    tire_circumference_mm: int | None = Field(None, gt=0)


class MotorcycleRead(BaseModel):
    """バイク情報のレスポンス。"""

    id: int
    name: str
    front_sprocket: int
    rear_sprocket: int
    chain_links: int
    tire_circumference_mm: int
    created_at: datetime
    updated_at: datetime

    # SQLAlchemyモデルからの自動変換を許可
    model_config = ConfigDict(from_attributes=True)