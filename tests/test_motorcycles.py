"""motorcycles APIのテスト。"""

SAMPLE_MOTORCYCLE = {
    "name": "MT-09 SP",
    "front_sprocket": 16,
    "rear_sprocket": 45,
    "chain_links": 118,
    "tire_circumference_mm": 1992,
}


def _create_motorcycle(client):
    """ヘルパー: バイクを1件作成して返す。"""
    res = client.post("/motorcycles", json=SAMPLE_MOTORCYCLE)
    assert res.status_code == 201
    return res.json()


class TestCreateMotorcycle:
    def test_success(self, client):
        res = client.post("/motorcycles", json=SAMPLE_MOTORCYCLE)
        assert res.status_code == 201
        body = res.json()
        assert body["name"] == "MT-09 SP"
        assert body["chain_links"] == 118
        assert "id" in body
        assert "created_at" in body

    def test_invalid_zero_sprocket(self, client):
        data = {**SAMPLE_MOTORCYCLE, "rear_sprocket": 0}
        res = client.post("/motorcycles", json=data)
        assert res.status_code == 422  # Pydanticバリデーションエラー

    def test_missing_required_field(self, client):
        data = {"name": "MT-09 SP"}  # 必須フィールド不足
        res = client.post("/motorcycles", json=data)
        assert res.status_code == 422


class TestReadMotorcycle:
    def test_get_one(self, client):
        created = _create_motorcycle(client)
        res = client.get(f"/motorcycles/{created['id']}")
        assert res.status_code == 200
        assert res.json()["name"] == "MT-09 SP"

    def test_not_found(self, client):
        res = client.get("/motorcycles/9999")
        assert res.status_code == 404

    def test_list(self, client):
        _create_motorcycle(client)
        res = client.get("/motorcycles")
        assert res.status_code == 200
        assert len(res.json()) == 1


class TestUpdateMotorcycle:
    def test_patch(self, client):
        created = _create_motorcycle(client)
        res = client.patch(
            f"/motorcycles/{created['id']}",
            json={"name": "MT-09 SP 2026"},
        )
        assert res.status_code == 200
        assert res.json()["name"] == "MT-09 SP 2026"
        # 他のフィールドは変わらない
        assert res.json()["chain_links"] == 118


class TestDeleteMotorcycle:
    def test_delete(self, client):
        created = _create_motorcycle(client)
        res = client.delete(f"/motorcycles/{created['id']}")
        assert res.status_code == 204
        # 削除後はGETで404
        res = client.get(f"/motorcycles/{created['id']}")
        assert res.status_code == 404


class TestChainStats:
    def test_stats(self, client):
        created = _create_motorcycle(client)
        res = client.get(f"/motorcycles/{created['id']}/chain-stats")
        assert res.status_code == 200
        body = res.json()
        assert body["wheel_rotations_per_chain_loop"] == 1.3111
        assert body["chain_distance_per_loop_m"] == 2.61
        assert body["distance_since_last_km"] is None  # メンテ記録なし
