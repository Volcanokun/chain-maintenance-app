"""スキーマパッケージ。"""

from app.schemas.maintenance_record import (
    MaintenanceRecordCreate,
    MaintenanceRecordRead,
    MaintenanceRecordUpdate,
)
from app.schemas.motorcycle import MotorcycleCreate, MotorcycleRead, MotorcycleUpdate

__all__ = [
    "MaintenanceRecordCreate",
    "MaintenanceRecordRead",
    "MaintenanceRecordUpdate",
    "MotorcycleCreate",
    "MotorcycleRead",
    "MotorcycleUpdate",
]
