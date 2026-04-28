"""チェーン計算ロジック。DB 非依存。"""

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainCalcResult:
    wheel_rotations_per_chain_loop: float
    chain_distance_per_loop_m: float
    tire_circumference_mm: int


def tire_size_to_circumference_mm(tire_size: str) -> int:
    """タイヤサイズ文字列（例: '180/55ZR17'）から円周(mm)を算出する。

    計算式: π × (リム径mm + サイドウォール高さ × 2)
    サイドウォール高さ = 幅mm × 偏平率 / 100
    """
    m = re.match(r"(\d+)/(\d+)[A-Z]*R?(\d+)", tire_size.strip())
    if not m:
        raise ValueError(f"タイヤサイズの形式が不正です: {tire_size!r}")
    width_mm = int(m.group(1))
    aspect = int(m.group(2))
    rim_inch = int(m.group(3))
    sidewall_mm = width_mm * aspect / 100
    diameter_mm = rim_inch * 25.4 + sidewall_mm * 2
    return round(math.pi * diameter_mm)


def calculate_chain_stats(
    chain_links: int,
    rear_sprocket: int,
    rear_tire_size: str,
) -> ChainCalcResult:
    """チェーン計算を行う。

    タイヤ回転数/チェーン1周 = コマ数 ÷ リアスプロケ丁数
      根拠: スプロケ1回転でチェーンが丁数コマ進む。
            チェーン1周(コマ数コマ)には コマ数÷丁数 回転必要。
    """
    circumference_mm = tire_size_to_circumference_mm(rear_tire_size)
    rotations = chain_links / rear_sprocket
    distance_m = rotations * circumference_mm / 1000
    return ChainCalcResult(
        wheel_rotations_per_chain_loop=round(rotations, 2),
        chain_distance_per_loop_m=round(distance_m, 1),
        tire_circumference_mm=circumference_mm,
    )
