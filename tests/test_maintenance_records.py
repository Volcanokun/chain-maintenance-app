"""maintenance_records APIのテスト。"""

SAMPLE_MOTORCYCLE = {
    "name": "MT-09 SP",
    "front_sprocket": 16,
    "rear_sprocket": 45,
    "chain_links": 118,
    "tire_circumference_mm": 1992,
}


def _create_motorcycle(client):
    res = client.post("/motorcycles", json=SAMPLE_MOTORCYCLE)
    assert res.status_code == 201
    return res.json()


def _create_record(client, motorcycle_id, odometer_km=15000, performed_at="2026-04-20"):
    data = {
        "motorcycle_id": motorcycle_id,
        "performed_at": performed_at,
        "odometer_km": odometer_km,
        "lubricant": "WAKO'S CHL",
        "notes": "チェーン清掃+注油",
    }
    res = client.post("/maintenance-records", json=data)
    assert res.status_code == 201
    return res.json()


class TestCreateRecord:
    def test_success(self, client):
        moto = _create_motorcycle(client)
        record = _create_record(client, moto["id"])
        assert record["odometer_km"] == 15000
        assert record["lubricant"] == "WAKO'S CHL"

    def test_motorcycle_not_found(self, client):
        data = {
            "motorcycle_id": 9999,
            "performed_at": "2026-04-20",
            "odometer_km": 15000,
        }
        res = client.post("/maintenance-records", json=data)
        assert res.status_code == 404

    def test_negative_odometer(self, client):
        moto = _create_motorcycle(client)
        data = {
            "motorcycle_id": moto["id"],
            "performed_at": "2026-04-20",
            "odometer_km": -1,
        }
        res = client.post("/maintenance-records", json=data)
        assert res.status_code == 422


class TestReadRecord:
    def test_get_one(self, client):
        moto = _create_motorcycle(client)
        record = _create_record(client, moto["id"])
        res = client.get(f"/maintenance-records/{record['id']}")
        assert res.status_code == 200

    def test_list_by_motorcycle(self, client):
        moto = _create_motorcycle(client)
        _create_record(client, moto["id"], 10000, "2026-03-01")
        _create_record(client, moto["id"], 15000, "2026-04-20")
        res = client.get(f"/maintenance-records/by-motorcycle/{moto['id']}")
        assert res.status_code == 200
        records = res.json()
        assert len(records) == 2
        # 降順確認(最新が先)
        assert records[0]["odometer_km"] == 15000

    def test_not_found(self, client):
        res = client.get("/maintenance-records/9999")
        assert res.status_code == 404


class TestUpdateRecord:
    def test_patch(self, client):
        moto = _create_motorcycle(client)
        record = _create_record(client, moto["id"])
        res = client.patch(
            f"/maintenance-records/{record['id']}",
            json={"odometer_km": 16000},
        )
        assert res.status_code == 200
        assert res.json()["odometer_km"] == 16000


class TestDeleteRecord:
    def test_delete(self, client):
        moto = _create_motorcycle(client)
        record = _create_record(client, moto["id"])
        res = client.delete(f"/maintenance-records/{record['id']}")
        assert res.status_code == 204

    def test_cascade_delete(self, client):
        """バイク削除でメンテ記録もCASCADE削除される。"""
        moto = _create_motorcycle(client)
        record = _create_record(client, moto["id"])
        # バイク削除
        client.delete(f"/motorcycles/{moto['id']}")
        # メンテ記録も消えている
        res = client.get(f"/maintenance-records/{record['id']}")
        assert res.status_code == 404
