"""maintenance_records APIエンドポイント。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.maintenance_record import (
    create_record,
    delete_record,
    get_record,
    get_records_by_motorcycle,
    update_record,
)
from app.crud.motorcycle import get_motorcycle
from app.db.session import get_db
from app.schemas.maintenance_record import (
    MaintenanceRecordCreate,
    MaintenanceRecordRead,
    MaintenanceRecordUpdate,
)

router = APIRouter(prefix="/maintenance-records", tags=["maintenance_records"])


@router.get(
    "/by-motorcycle/{motorcycle_id}",
    response_model=list[MaintenanceRecordRead],
)
def list_by_motorcycle(motorcycle_id: int, db: Session = Depends(get_db)):
    """指定バイクのメンテ記録を実施日降順で取得。"""
    motorcycle = get_motorcycle(db, motorcycle_id)
    if motorcycle is None:
        raise HTTPException(status_code=404, detail="Motorcycle not found")
    return get_records_by_motorcycle(db, motorcycle_id)


@router.get("/{record_id}", response_model=MaintenanceRecordRead)
def read_record(record_id: int, db: Session = Depends(get_db)):
    """メンテ記録を1件取得。"""
    obj = get_record(db, record_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return obj


@router.post(
    "",
    response_model=MaintenanceRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create(data: MaintenanceRecordCreate, db: Session = Depends(get_db)):
    """メンテ記録を新規登録。"""
    motorcycle = get_motorcycle(db, data.motorcycle_id)
    if motorcycle is None:
        raise HTTPException(status_code=404, detail="Motorcycle not found")
    return create_record(db, data)


@router.patch("/{record_id}", response_model=MaintenanceRecordRead)
def update(
    record_id: int,
    data: MaintenanceRecordUpdate,
    db: Session = Depends(get_db),
):
    """メンテ記録を部分更新。"""
    obj = get_record(db, record_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return update_record(db, obj, data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(record_id: int, db: Session = Depends(get_db)):
    """メンテ記録を削除。"""
    obj = get_record(db, record_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Record not found")
    delete_record(db, obj)