"""motorcycles CRUD操作。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.motorcycle import Motorcycle
from app.schemas.motorcycle import MotorcycleCreate, MotorcycleUpdate


def get_motorcycle(db: Session, motorcycle_id: int) -> Motorcycle | None:
    """IDでバイクを1件取得。"""
    return db.get(Motorcycle, motorcycle_id)


def get_motorcycles(db: Session) -> list[Motorcycle]:
    """バイク一覧を取得。"""
    stmt = select(Motorcycle).order_by(Motorcycle.id)
    return list(db.scalars(stmt).all())


def create_motorcycle(db: Session, data: MotorcycleCreate) -> Motorcycle:
    """バイクを新規登録。"""
    obj = Motorcycle(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_motorcycle(
    db: Session, motorcycle: Motorcycle, data: MotorcycleUpdate
) -> Motorcycle:
    """バイク情報を部分更新。"""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(motorcycle, key, value)
    db.commit()
    db.refresh(motorcycle)
    return motorcycle


def delete_motorcycle(db: Session, motorcycle: Motorcycle) -> None:
    """バイクを削除(CASCADE で関連レコードも削除)。"""
    db.delete(motorcycle)
    db.commit()