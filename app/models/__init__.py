"""モデルパッケージ。

Alembicがモデルを認識できるよう、全モデルをここでimportする。
"""
from app.models.maintenance_record import MaintenanceRecord
from app.models.motorcycle import Motorcycle

__all__ = ["MaintenanceRecord", "Motorcycle"]