"""motorcycles APIエンドポイント。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.motorcycle import (
    create_motorcycle,
    delete_motorcycle,
    get_motorcycle,
    get_motorcycles,
    update_motorcycle,
)
from app.db.session import get_db
from app.schemas.motorcycle import MotorcycleCreate, MotorcycleRead, MotorcycleUpdate
from app.services.chain_calculator import ChainCalcResult, calculate_chain_stats

router = APIRouter(prefix="/motorcycles", tags=["motorcycles"])


@router.get("", response_model=list[MotorcycleRead])
def list_motorcycles(db: Session = Depends(get_db)):
    """バイク一覧を取得。"""
    return get_motorcycles(db)


@router.get("/{motorcycle_id}", response_model=MotorcycleRead)
def read_motorcycle(motorcycle_id: int, db: Session = Depends(get_db)):
    """バイクを1件取得。"""
    obj = get_motorcycle(db, motorcycle_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Motorcycle not found")
    return obj


@router.post("", response_model=MotorcycleRead, status_code=status.HTTP_201_CREATED)
def create(data: MotorcycleCreate, db: Session = Depends(get_db)):
    """バイクを新規登録。"""
    return create_motorcycle(db, data)


@router.patch("/{motorcycle_id}", response_model=MotorcycleRead)
def update(motorcycle_id: int, data: MotorcycleUpdate, db: Session = Depends(get_db)):
    """バイク情報を部分更新。"""
    obj = get_motorcycle(db, motorcycle_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Motorcycle not found")
    return update_motorcycle(db, obj, data)


@router.delete("/{motorcycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(motorcycle_id: int, db: Session = Depends(get_db)):
    """バイクを削除。関連メンテ記録もCASCADE削除される。"""
    obj = get_motorcycle(db, motorcycle_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Motorcycle not found")
    delete_motorcycle(db, obj)


@router.get("/{motorcycle_id}/chain-stats", response_model=ChainCalcResult)
def chain_stats(motorcycle_id: int, db: Session = Depends(get_db)):
    """指定バイクのチェーン計算結果を取得。"""
    from app.crud.maintenance_record import get_latest_record

    obj = get_motorcycle(db, motorcycle_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Motorcycle not found")

    latest = get_latest_record(db, motorcycle_id)
    last_odometer = latest.odometer_km if latest else None

    return calculate_chain_stats(
        chain_links=obj.chain_links,
        rear_sprocket=obj.rear_sprocket,
        tire_circumference_mm=obj.tire_circumference_mm,
        last_maintenance_odometer_km=last_odometer,
    )
