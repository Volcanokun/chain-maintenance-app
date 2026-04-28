"""
Locust 負荷試験: ECS Auto Scaling 検証 + Aurora Serverless v2 ウォームアップ

インストール:
  pip install locust
  # または uv を使う場合:
  uv tool install locust

実行方法 (Web UI):
  locust -f locustfile.py --host https://chain-app.volcanokun.dev
  → ブラウザで http://localhost:8089 を開く
  → Users: 50, Spawn rate: 5 で Start

実行方法 (ヘッドレス):
  locust -f locustfile.py --host https://chain-app.volcanokun.dev \\
    --users 50 --spawn-rate 5 --run-time 5m --headless

Auto Scaling 検証の目安:
  - ECS タスク: 0.25 vCPU / CPU 目標: 60%
  - 50 ユーザー程度で CPU > 60% を超え、スケールアウトが発火する
  - CloudWatch メトリクス: ECS → chain-maintenance-prod-cluster → CPUUtilization
"""

import random
from datetime import date, timedelta

from locust import HttpUser, between, task

_MOTORCYCLE_PRESETS = [
    {"name": "MT-09 SP", "front_sprocket": 16, "rear_sprocket": 45,
     "chain_links": 118, "tire_circumference_mm": 1992},
    {"name": "CBR600RR", "front_sprocket": 15, "rear_sprocket": 40,
     "chain_links": 112, "tire_circumference_mm": 1880},
    {"name": "Z900RS", "front_sprocket": 15, "rear_sprocket": 41,
     "chain_links": 116, "tire_circumference_mm": 1960},
    {"name": "S1000RR", "front_sprocket": 17, "rear_sprocket": 44,
     "chain_links": 118, "tire_circumference_mm": 1972},
    {"name": "Ninja ZX-6R", "front_sprocket": 15, "rear_sprocket": 42,
     "chain_links": 112, "tire_circumference_mm": 1875},
    {"name": "GSX-R750", "front_sprocket": 17, "rear_sprocket": 43,
     "chain_links": 114, "tire_circumference_mm": 1895},
]

_LUBRICANTS = ["WAKO'S CHL", "MOTUL C3", "DID ルブリカント", "YAMAHA Chain Lube", None]


class ChainAppUser(HttpUser):
    """
    リアルなユーザー行動をシミュレート。

    フロー:
      on_start → /health + /motorcycles でウォームアップ
               → バイク1台を登録し、メンテ記録3件をシード
      tasks    → 読み取り中心 (list / chain-stats) + 書き込み (record 追加)
      on_stop  → 登録したバイクを削除 (CASCADE でメンテ記録も削除)
    """

    wait_time = between(1, 3)

    # ── セットアップ / ティアダウン ──────────────────────────────────────────

    def on_start(self):
        """
        Aurora Serverless v2 のコールドスタート対策ウォームアップ。
        /health → /motorcycles の順に叩いて DB 接続を確立してから
        テスト用データを登録する。
        """
        self.motorcycle_id: int | None = None

        # ウォームアップリクエスト (Aurora が寝ている場合に接続を確立する)
        self.client.get("/health",       name="/health [warmup]")
        self.client.get("/motorcycles",  name="/motorcycles [warmup]")

        # テスト用バイクを登録
        preset = random.choice(_MOTORCYCLE_PRESETS)
        payload = {**preset, "name": f"{preset['name']} [test-{random.randint(1000, 9999)}]"}

        resp = self.client.post("/motorcycles", json=payload, name="/motorcycles [setup]")
        if resp.status_code == 201:
            self.motorcycle_id = resp.json()["id"]
            self._seed_maintenance_records()

    def _seed_maintenance_records(self) -> None:
        """テスト用バイクに初期メンテ記録を3件挿入する。"""
        base_km = random.randint(5000, 20000)
        for i in range(3):
            self.client.post(
                "/maintenance-records",
                json={
                    "motorcycle_id": self.motorcycle_id,
                    "performed_at":  str(date.today() - timedelta(days=90 - i * 30)),
                    "odometer_km":   base_km + i * 500,
                    "lubricant":     random.choice(_LUBRICANTS),
                    "notes":         f"負荷試験シードデータ #{i + 1}",
                },
                name="/maintenance-records [seed]",
            )

    def on_stop(self) -> None:
        """テスト終了時にテスト用バイクを削除 (メンテ記録も CASCADE 削除)。"""
        if self.motorcycle_id:
            self.client.delete(
                f"/motorcycles/{self.motorcycle_id}",
                name="/motorcycles/{id} [cleanup]",
            )

    # ── タスク (weight = 相対的な呼び出し頻度) ──────────────────────────────

    @task(5)
    def get_health(self):
        """ヘルスチェック (軽量・高頻度)。ALB ヘルスチェックと同等の負荷を再現。"""
        self.client.get("/health")

    @task(10)
    def list_motorcycles(self):
        """バイク一覧取得。全件 SELECT → READ heavy シナリオのベース。"""
        self.client.get("/motorcycles")

    @task(8)
    def get_chain_stats(self):
        """チェーン計算。Python 計算 + DB クエリが混在する CPU ヒット系エンドポイント。"""
        if self.motorcycle_id:
            self.client.get(
                f"/motorcycles/{self.motorcycle_id}/chain-stats",
                name="/motorcycles/{id}/chain-stats",
            )

    @task(6)
    def list_maintenance_records(self):
        """メンテ記録一覧取得。motorcycle_id フィルタ付き SELECT。"""
        if self.motorcycle_id:
            self.client.get(
                f"/maintenance-records/by-motorcycle/{self.motorcycle_id}",
                name="/maintenance-records/by-motorcycle/{id}",
            )

    @task(3)
    def create_maintenance_record(self):
        """メンテ記録登録 (WRITE)。INSERT → RETURNING のラウンドトリップ。"""
        if self.motorcycle_id:
            self.client.post(
                "/maintenance-records",
                json={
                    "motorcycle_id": self.motorcycle_id,
                    "performed_at":  str(date.today()),
                    "odometer_km":   random.randint(1000, 50000),
                    "lubricant":     random.choice(_LUBRICANTS),
                    "notes":         "負荷試験 write タスク",
                },
                name="/maintenance-records [write]",
            )

    @task(1)
    def patch_motorcycle(self):
        """バイク情報部分更新 (低頻度 PATCH)。chain_links をランダム更新。"""
        if self.motorcycle_id:
            self.client.patch(
                f"/motorcycles/{self.motorcycle_id}",
                json={"chain_links": random.randint(110, 130)},
                name="/motorcycles/{id} [patch]",
            )
