"""maintenance_records CRUD操作。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.maintenance_record import MaintenanceRecord
from app.schemas.maintenance_record import (
    MaintenanceRecordCreate,
    MaintenanceRecordUpdate,
)


def get_record(db: Session, record_id: int) -> MaintenanceRecord | None:
    """IDでメンテ記録を1件取得。"""
    return db.get(MaintenanceRecord, record_id)


def get_records_by_motorcycle(
    db: Session, motorcycle_id: int
) -> list[MaintenanceRecord]:
    """指定バイクのメンテ記録を実施日降順で取得。"""
    stmt = (
        select(MaintenanceRecord)
        .where(MaintenanceRecord.motorcycle_id == motorcycle_id)
        .order_by(MaintenanceRecord.performed_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_latest_record(
    db: Session, motorcycle_id: int
) -> MaintenanceRecord | None:
    """指定バイクの最新メンテ記録を取得。"""
    stmt = (
        select(MaintenanceRecord)
        .where(MaintenanceRecord.motorcycle_id == motorcycle_id)
        .order_by(MaintenanceRecord.performed_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def create_record(
    db: Session, data: MaintenanceRecordCreate
) -> MaintenanceRecord:
    """メンテ記録を新規登録。"""
    obj = MaintenanceRecord(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_record(
    db: Session, record: MaintenanceRecord, data: MaintenanceRecordUpdate
) -> MaintenanceRecord:
    """メンテ記録を部分更新。"""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: MaintenanceRecord) -> None:
    """メンテ記録を削除。"""
    db.delete(record)
    db.commit()