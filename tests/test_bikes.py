"""バイクマスターAPI エンドポイントのテスト。"""

import pytest

from app.models.bike_master import BikeMaster


def _seed(db_session, **kwargs) -> BikeMaster:
    defaults = dict(
        maker="ホンダ",
        model_name="CB400SF",
        displacement_cc=400,
        front_sprocket=15,
        rear_sprocket=39,
        chain_links=108,
        chain_pitch="525",
        rear_tire_size="160/60ZR17",
    )
    defaults.update(kwargs)
    bike = BikeMaster(**defaults)
    db_session.add(bike)
    db_session.commit()
    db_session.refresh(bike)
    return bike


class TestMakes:
    def test_returns_makers_sorted(self, client, db_session):
        _seed(db_session, maker="ヤマハ")
        _seed(db_session, maker="ホンダ", model_name="CBR1000RR", displacement_cc=1000)
        res = client.get("/makes")
        assert res.status_code == 200
        makes = res.json()
        assert "ホンダ" in makes
        assert "ヤマハ" in makes
        assert makes == sorted(makes)

    def test_empty_when_no_data(self, client):
        res = client.get("/makes")
        assert res.status_code == 200
        assert res.json() == []


class TestDisplacements:
    def test_returns_sorted_displacements_for_maker(self, client, db_session):
        _seed(db_session, displacement_cc=400)
        _seed(db_session, model_name="CBR1000RR", displacement_cc=1000)
        res = client.get("/displacements?make=ホンダ")
        assert res.status_code == 200
        assert res.json() == [400, 1000]

    def test_excludes_other_maker(self, client, db_session):
        _seed(db_session, maker="ヤマハ", displacement_cc=600)
        _seed(db_session, displacement_cc=400)
        res = client.get("/displacements?make=ホンダ")
        assert res.status_code == 200
        assert res.json() == [400]

    def test_empty_for_unknown_maker(self, client):
        res = client.get("/displacements?make=存在しないメーカー")
        assert res.status_code == 200
        assert res.json() == []


class TestBikes:
    def test_returns_bikes_matching_maker_and_displacement(self, client, db_session):
        bike = _seed(db_session, displacement_cc=400)
        _seed(db_session, model_name="CBR1000RR", displacement_cc=1000)
        res = client.get("/bikes?make=ホンダ&displacement_cc=400")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == bike.id
        assert data[0]["model_name"] == "CB400SF"

    def test_returns_all_required_fields(self, client, db_session):
        _seed(db_session)
        res = client.get("/bikes?make=ホンダ&displacement_cc=400")
        assert res.status_code == 200
        b = res.json()[0]
        for field in (
            "id",
            "maker",
            "model_name",
            "displacement_cc",
            "front_sprocket",
            "rear_sprocket",
            "chain_links",
            "chain_pitch",
            "rear_tire_size",
        ):
            assert field in b

    def test_empty_for_no_match(self, client):
        res = client.get("/bikes?make=ホンダ&displacement_cc=9999")
        assert res.status_code == 200
        assert res.json() == []


class TestBikeStats:
    def test_stats_calculation(self, client, db_session):
        bike = _seed(
            db_session,
            front_sprocket=15,
            rear_sprocket=39,
            chain_links=108,
            rear_tire_size="160/60ZR17",
        )
        res = client.get(f"/bikes/{bike.id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["bike"]["id"] == bike.id
        # 108 / 39 ≒ 2.77
        assert data["wheel_rotations_per_chain_loop"] == pytest.approx(2.77, abs=0.01)
        assert data["tire_circumference_mm"] > 0
        assert data["chain_distance_per_loop_m"] > 0

    def test_returns_404_for_unknown_id(self, client):
        res = client.get("/bikes/99999/stats")
        assert res.status_code == 404

    def test_stats_values_are_positive(self, client, db_session):
        bike = _seed(db_session)
        res = client.get(f"/bikes/{bike.id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["wheel_rotations_per_chain_loop"] > 0
        assert data["chain_distance_per_loop_m"] > 0
        assert data["tire_circumference_mm"] > 0
