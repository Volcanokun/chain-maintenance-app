"""バイクマスター API エンドポイント。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.bike_master import BikeMaster
from app.schemas.bike_master import BikeMasterRead, ChainStatsResponse
from app.services.chain_calculator import calculate_chain_stats

router = APIRouter(tags=["bikes"])


@router.get("/makes", response_model=list[str])
def list_makes(db: Session = Depends(get_db)):
    """メーカー一覧（五十音順）。"""
    rows = db.execute(select(distinct(BikeMaster.maker)).order_by(BikeMaster.maker)).scalars()
    return list(rows)


@router.get("/displacements", response_model=list[int])
def list_displacements(make: str, db: Session = Depends(get_db)):
    """指定メーカーの排気量一覧（昇順）。"""
    rows = db.execute(
        select(distinct(BikeMaster.displacement_cc))
        .where(BikeMaster.maker == make, BikeMaster.displacement_cc.is_not(None))
        .order_by(BikeMaster.displacement_cc)
    ).scalars()
    return list(rows)


@router.get("/bikes", response_model=list[BikeMasterRead])
def list_bikes(
    make: str,
    displacement_cc: int | None = None,
    displacement_min: int | None = None,
    displacement_max: int | None = None,
    db: Session = Depends(get_db),
):
    """メーカー＋排気量条件で絞り込んだ車種一覧（モデル名昇順）。"""
    query = select(BikeMaster).where(BikeMaster.maker == make)
    if displacement_cc is not None:
        query = query.where(BikeMaster.displacement_cc == displacement_cc)
    else:
        if displacement_min is not None:
            query = query.where(BikeMaster.displacement_cc >= displacement_min)
        if displacement_max is not None:
            query = query.where(BikeMaster.displacement_cc <= displacement_max)
    rows = db.execute(query.order_by(BikeMaster.model_name)).scalars()
    return list(rows)


@router.get("/bikes/{bike_id}/stats", response_model=ChainStatsResponse)
def bike_stats(bike_id: int, db: Session = Depends(get_db)):
    """指定車種のチェーン計算結果。"""
    bike = db.get(BikeMaster, bike_id)
    if bike is None:
        raise HTTPException(status_code=404, detail="Bike not found")
    try:
        result = calculate_chain_stats(
            chain_links=bike.chain_links,
            rear_sprocket=bike.rear_sprocket,
            rear_tire_size=bike.rear_tire_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ChainStatsResponse(
        bike=BikeMasterRead.model_validate(bike),
        wheel_rotations_per_chain_loop=result.wheel_rotations_per_chain_loop,
        chain_distance_per_loop_m=result.chain_distance_per_loop_m,
        tire_circumference_mm=result.tire_circumference_mm,
    )
