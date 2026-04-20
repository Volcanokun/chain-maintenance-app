"""チェーンメンテナンス計算ロジック。

DB非依存。純粋な計算のみ。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainCalcResult:
    """計算結果を格納する値オブジェクト。"""

    wheel_rotations_per_chain_loop: float
    chain_distance_per_loop_m: float
    distance_since_last_km: int | None


def calc_wheel_rotations(chain_links: int, rear_sprocket: int) -> float:
    """チェーン1周あたりのホイール回転数を算出。

    式: ホイール回転数 = チェーンコマ数 / (リアスプロケ丁数 × 2)
    リアスプロケ1回転でチェーンが「丁数×2コマ」進む原理。
    """
    return chain_links / (rear_sprocket * 2)


def calc_chain_distance_per_loop(
    chain_links: int,
    rear_sprocket: int,
    tire_circumference_mm: int,
) -> float:
    """チェーン1周あたりの走行距離(メートル)を算出。

    ホイール回転数 × タイヤ円周 = 1ループあたりの走行距離。
    """
    rotations = calc_wheel_rotations(chain_links, rear_sprocket)
    return rotations * tire_circumference_mm / 1000  # mm → m


def calculate_chain_stats(
    chain_links: int,
    rear_sprocket: int,
    tire_circumference_mm: int,
    current_odometer_km: int | None = None,
    last_maintenance_odometer_km: int | None = None,
) -> ChainCalcResult:
    """チェーンメンテナンス統計を一括計算。

    Args:
        chain_links: チェーンコマ数
        rear_sprocket: リアスプロケ丁数
        tire_circumference_mm: リアタイヤ円周(mm)
        current_odometer_km: 現在走行距離(任意)
        last_maintenance_odometer_km: 前回メンテ時の走行距離(任意)

    Returns:
        ChainCalcResult: 計算結果
    """
    rotations = calc_wheel_rotations(chain_links, rear_sprocket)
    distance_per_loop = calc_chain_distance_per_loop(
        chain_links, rear_sprocket, tire_circumference_mm
    )

    distance_since_last: int | None = None
    if current_odometer_km is not None and last_maintenance_odometer_km is not None:
        distance_since_last = current_odometer_km - last_maintenance_odometer_km

    return ChainCalcResult(
        wheel_rotations_per_chain_loop=round(rotations, 4),
        chain_distance_per_loop_m=round(distance_per_loop, 2),
        distance_since_last_km=distance_since_last,
    )