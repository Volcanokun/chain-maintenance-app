"""maintenance_records APIの入出力スキーマ。"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceRecordCreate(BaseModel):
    """メンテ記録登録時の入力。"""

    motorcycle_id: int = Field(..., gt=0)
    performed_at: date = Field(..., examples=["2026-04-20"])
    odometer_km: int = Field(..., ge=0, examples=[15000])
    lubricant: str | None = Field(None, max_length=100, examples=["WAKO'S CHL"])
    notes: str | None = Field(None, examples=["チェーン清掃+注油"])


class MaintenanceRecordUpdate(BaseModel):
    """メンテ記録更新時の入力。"""

    performed_at: date | None = None
    odometer_km: int | None = Field(None, ge=0)
    lubricant: str | None = Field(None, max_length=100)
    notes: str | None = None


class MaintenanceRecordRead(BaseModel):
    """メンテ記録のレスポンス。"""

    id: int
    motorcycle_id: int
    performed_at: date
    odometer_km: int
    lubricant: str | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
