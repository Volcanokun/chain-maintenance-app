"""bike_masters API のスキーマ。"""

from pydantic import BaseModel, ConfigDict


class BikeMasterRead(BaseModel):
    id: int
    maker: str
    model_name: str
    displacement_cc: int | None
    front_sprocket: int
    rear_sprocket: int
    chain_links: int
    chain_pitch: str | None
    rear_tire_size: str

    model_config = ConfigDict(from_attributes=True)


class ChainStatsResponse(BaseModel):
    bike: BikeMasterRead
    wheel_rotations_per_chain_loop: float
    chain_distance_per_loop_m: float
    tire_circumference_mm: int
