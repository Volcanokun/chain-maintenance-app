"""バイクブロスからメーカー単位でスペックをスクレイピングしてDBに投入する。

使い方:
    uv run python scripts/scrape_maker.py --maker ヤマハ
    uv run python scripts/scrape_maker.py --maker スズキ --dry-run
    uv run python scripts/scrape_maker.py --maker カワサキ --range 4  # 251-400ccのみ

排気量カテゴリ（バイクブロスの v パラメータ）:
    1=50cc以下  2=51-125cc  3=126-250cc  4=251-400cc
    5=401-750cc  6=751-1000cc  7=1001cc以上  8=その他
"""

import argparse
import re
import sys
import time

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

sys.path.insert(0, ".")
from app.db.session import SessionLocal
from app.models.bike_master import BikeMaster

BASE_URL = "https://www.bikebros.co.jp"
REQUEST_DELAY = 0.5

# v=1（50cc以下）、v=2（51-125cc）はスクーターがほぼ全てベルト駆動のためデフォルトはスキップ
CC_RANGES_DEFAULT = list(range(3, 9))  # 3〜8（126cc以上）

MAKER_ID_MAP: dict[str, int] = {
    "ホンダ": 1,
    "ヤマハ": 2,
    "スズキ": 3,
    "カワサキ": 4,
    "ハーレーダビッドソン": 5,
    "BMW": 7,
    "ドゥカティ": 8,
    "トライアンフ": 10,
    "KTM": 33,
}

CC_RANGES_ALL = list(range(1, 9))  # 1〜8


def get(url: str, client: httpx.Client) -> BeautifulSoup:
    res = client.get(url, timeout=30, follow_redirects=True)
    res.raise_for_status()
    time.sleep(REQUEST_DELAY)
    return BeautifulSoup(res.text, "lxml")


def fetch_model_group_urls(maker_id: int, v: int, client: httpx.Client) -> list[str]:
    """排気量カテゴリページからモデルグループURLを取得する。"""
    url = f"{BASE_URL}/catalog/{maker_id}/?v={v}"
    soup = get(url, client)
    pattern = re.compile(rf"^/catalog/{maker_id}/\d+_\d+/$")
    seen: set[str] = set()
    results: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if pattern.match(href) and href not in seen:
            seen.add(href)
            results.append(BASE_URL + href)
    return results


def fetch_variant_urls(model_group_url: str, maker_id: int, client: httpx.Client) -> list[str]:
    """モデルグループページから年式バリアントURLを取得する。"""
    soup = get(model_group_url, client)
    pattern = re.compile(rf"^/catalog/{maker_id}/\d+_\d+/(\d+)/")
    seen: set[str] = set()
    results: list[str] = []
    for a in soup.find_all("a", href=True):
        m = pattern.match(a["href"])
        if m:
            clean = f"/catalog/{maker_id}/" + a["href"].split("/")[3] + f"/{m.group(1)}/"
            if clean not in seen:
                seen.add(clean)
                results.append(BASE_URL + clean)
    return results


def fetch_variant_spec(
    variant_url: str, maker_name: str, client: httpx.Client
) -> dict | None:
    """バリアントページからチェーン関連スペックを取得する。"""
    soup = get(variant_url, client)

    spec: dict[str, str] = {}
    for row in soup.select("tr"):
        th = row.find("th")
        td = row.find("td")
        if th and td:
            spec[th.get_text(strip=True)] = td.get_text(strip=True)

    # チェーン駆動のバイクのみ対象
    if spec.get("動力伝達方式", "") != "チェーン":
        return None

    try:
        return {
            "maker": maker_name,
            "model_name": spec["タイプグレード名"],
            "displacement_cc": _to_int(spec.get("排気量 (cc)")),
            "front_sprocket": int(spec["スプロケット歯数・前"]),
            "rear_sprocket": int(spec["スプロケット歯数・後"]),
            "chain_links": int(spec["標準チェーンリンク数"]),
            "chain_pitch": spec.get("チェーンサイズ") or None,
            "rear_tire_size": spec["タイヤ（後）"],
        }
    except (KeyError, ValueError):
        return None


def _to_int(s: str | None) -> int | None:
    if not s:
        return None
    cleaned = s.replace(",", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


def scrape_maker(maker_name: str, ranges: list[int]) -> list[dict]:
    maker_id = MAKER_ID_MAP.get(maker_name)
    if maker_id is None:
        raise ValueError(f"未対応のメーカー: {maker_name}。MAKER_ID_MAP を確認してください。")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    all_bikes: list[dict] = []
    seen_models: set[str] = set()

    with httpx.Client(headers=headers) as client:
        for v in ranges:
            print(f"[{maker_name}] 排気量カテゴリ v={v} ...", flush=True)
            model_groups = fetch_model_group_urls(maker_id, v, client)
            print(f"  モデルグループ: {len(model_groups)} 件")

            for i, group_url in enumerate(model_groups, 1):
                print(f"  [{i}/{len(model_groups)}] {group_url} ...", end=" ", flush=True)
                try:
                    variants = fetch_variant_urls(group_url, maker_id, client)
                except Exception as e:
                    print(f"スキップ ({e})")
                    continue

                group_bikes = 0
                for vurl in variants:
                    try:
                        data = fetch_variant_spec(vurl, maker_name, client)
                    except Exception:
                        continue
                    if data is None:
                        continue
                    key = data["model_name"]
                    if key in seen_models:
                        continue
                    seen_models.add(key)
                    all_bikes.append(data)
                    group_bikes += 1

                print(f"{group_bikes} 件")

    return all_bikes


def upsert_bikes(bikes: list[dict], db: Session) -> tuple[int, int]:
    added, updated = 0, 0
    for data in bikes:
        existing = (
            db.query(BikeMaster)
            .filter_by(maker=data["maker"], model_name=data["model_name"])
            .first()
        )
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(BikeMaster(**data))
            added += 1
    db.commit()
    return added, updated


def main() -> None:
    parser = argparse.ArgumentParser(description="バイクブロスからメーカー単位でスクレイピング")
    parser.add_argument(
        "--maker", required=True,
        help=f"メーカー名。対応: {list(MAKER_ID_MAP.keys())}"
    )
    parser.add_argument(
        "--range", dest="range_v", type=int, default=None,
        help="排気量カテゴリのみ取得 (1-8)。省略時は全カテゴリ"
    )
    parser.add_argument("--dry-run", action="store_true", help="DBに書き込まず結果を表示のみ")
    args = parser.parse_args()

    ranges = [args.range_v] if args.range_v else CC_RANGES_DEFAULT

    bikes = scrape_maker(args.maker, ranges)
    print(f"\n合計 {len(bikes)} 件取得")

    if args.dry_run:
        print("--dry-run: DBへの書き込みをスキップ")
        for b in bikes[:10]:
            print(" ", b)
        return

    db = SessionLocal()
    try:
        added, updated = upsert_bikes(bikes, db)
        print(f"DB投入完了: {added} 件追加, {updated} 件更新")
    finally:
        db.close()


if __name__ == "__main__":
    main()
