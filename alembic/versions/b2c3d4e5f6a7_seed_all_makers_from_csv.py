"""seed: add unique constraint and upsert all makers from data/bike_masters.csv

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-04

(maker, model_name) にユニーク制約を追加し、
CSV（data/bike_masters.csv）を読み込んで bike_masters テーブルへ upsert する。
スクレイパー再実行 → CSV 更新 → alembic upgrade head で常に最新データに同期できる。
"""

import csv
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

CSV_PATH = Path(__file__).parents[2] / "data" / "bike_masters.csv"


def upgrade() -> None:
    # (maker, model_name) にユニーク制約を追加（ON CONFLICT で upsert するために必要）
    op.create_unique_constraint(
        "uq_bike_masters_maker_model",
        "bike_masters",
        ["maker", "model_name"],
    )

    conn = op.get_bind()

    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        conn.execute(
            sa.text("""
                INSERT INTO bike_masters
                    (maker, model_name, displacement_cc,
                     front_sprocket, rear_sprocket, chain_links,
                     chain_pitch, rear_tire_size)
                VALUES
                    (:maker, :model_name, :displacement_cc,
                     :front_sprocket, :rear_sprocket, :chain_links,
                     :chain_pitch, :rear_tire_size)
                ON CONFLICT ON CONSTRAINT uq_bike_masters_maker_model DO UPDATE SET
                    displacement_cc = EXCLUDED.displacement_cc,
                    front_sprocket  = EXCLUDED.front_sprocket,
                    rear_sprocket   = EXCLUDED.rear_sprocket,
                    chain_links     = EXCLUDED.chain_links,
                    chain_pitch     = EXCLUDED.chain_pitch,
                    rear_tire_size  = EXCLUDED.rear_tire_size
            """),
            {
                "maker":           row["maker"],
                "model_name":      row["model_name"],
                "displacement_cc": int(row["displacement_cc"]) if row["displacement_cc"] else None,
                "front_sprocket":  int(row["front_sprocket"]),
                "rear_sprocket":   int(row["rear_sprocket"]),
                "chain_links":     int(row["chain_links"]),
                "chain_pitch":     row["chain_pitch"] or None,
                "rear_tire_size":  row["rear_tire_size"],
            },
        )


def downgrade() -> None:
    op.drop_constraint("uq_bike_masters_maker_model", "bike_masters", type_="unique")
    op.execute(sa.text("DELETE FROM bike_masters WHERE maker != 'ホンダ'"))
