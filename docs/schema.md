# DBスキーマ設計 - Bike Specs Lookup App

## 設計方針

- **シンプルさ優先**: 1テーブル構成（バイクスペックマスタのみ）
- **読み取り専用**: アプリからの書き込みなし。データ更新はスクレイパー + CSVマイグレーション経由
- **インデックス最小化**: 検索対象（maker / displacement_cc）のみに絞る

> **変更履歴**: Phase 1 では `motorcycles` / `maintenance_records` の2テーブル構成だったが、
> Phase 3-B のピボットで `bike_masters` 1テーブルに全面移行した（Alembicマイグレーション `a1b2c3d4e5f6`）。

## ER図

```
┌──────────────────────────────────────────┐
│  bike_masters                            │
├──────────────────────────────────────────┤
│ id              INTEGER  PK              │
│ maker           VARCHAR(100)  NOT NULL   │
│ model_name      VARCHAR(200)  NOT NULL   │
│ displacement_cc INTEGER  NULL            │
│ front_sprocket  INTEGER  NOT NULL        │
│ rear_sprocket   INTEGER  NOT NULL        │
│ chain_links     INTEGER  NOT NULL        │
│ chain_pitch     VARCHAR(10)  NULL        │
│ rear_tire_size  VARCHAR(30)  NOT NULL    │
└──────────────────────────────────────────┘
```

## テーブル定義

### bike_masters

バイクのチェーン関連スペックを保持するマスタテーブル。
バイクブロスからスクレイピングした情報を格納する。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY | 自動採番 |
| maker | VARCHAR(100) | NOT NULL | メーカー名（例: "ヤマハ"） |
| model_name | VARCHAR(200) | NOT NULL | 車種名・グレード名（例: "MT-09 SP"） |
| displacement_cc | INTEGER | NULL可 | 排気量（cc）。不明な場合はNULL |
| front_sprocket | INTEGER | NOT NULL | 前スプロケット歯数 |
| rear_sprocket | INTEGER | NOT NULL | 後スプロケット歯数 |
| chain_links | INTEGER | NOT NULL | 標準チェーンコマ数 |
| chain_pitch | VARCHAR(10) | NULL可 | チェーンサイズ（例: "525", "520"） |
| rear_tire_size | VARCHAR(30) | NOT NULL | リアタイヤサイズ（例: "180/55ZR17"） |

## インデックス

```sql
CREATE INDEX ix_bike_masters_maker ON bike_masters(maker);
CREATE INDEX ix_bike_masters_displacement_cc ON bike_masters(displacement_cc);
```

**判断根拠**: 主要クエリは「メーカー絞り込み」と「排気量範囲フィルタ」の組み合わせ。
それ以外のカラムでの検索はないため、インデックスはこの2本のみ。

## データ投入フロー

```
scripts/scrape_maker.py --all-makers --csv data/bike_masters.csv
          ↓
  data/bike_masters.csv をコミット
          ↓
  alembic upgrade head（CI/CDで自動実行）
          ↓
  マイグレーションが CSV を読んで bulk_insert
```

### 対応メーカー（現在）

| メーカー | 件数 |
|---|---|
| ホンダ | 392件 |
| カワサキ | 306件 |
| ヤマハ | 231件 |
| スズキ | 164件 |
| トライアンフ | 39件 |
| **合計** | **1,132件** |

> ハーレーダビッドソン・BMW・ドゥカティ・KTMはベルト/シャフト駆動モデルが多く、
> バイクブロスのカタログでチェーン駆動として登録されているモデルが0件のため対象外。

対象: 126cc以上のチェーン駆動モデル（ベルト・シャフト駆動は除外）

## マイグレーション戦略

- **Alembic** でバージョン管理
- 各マイグレーションは **1機能1ファイル**
- 本番（Aurora）への適用はCI/CD経由のみ、手動でSQL直接実行はしない
- スキーマ変更とデータシードを同一マイグレーションファイルにまとめる方針

## 制約事項

- **重複管理**: `(maker, model_name)` の組み合わせで重複排除（upsert）
- **削除ポリシー**: 物理削除のみ（論理削除は実装しない）
- **書き込みAPI**: アプリからの直接書き込みエンドポイントなし（読み取り専用）
