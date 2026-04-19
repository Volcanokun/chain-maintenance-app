# DBスキーマ設計 - Chain Maintenance App

## 設計方針

- **シンプルさ優先**: 2テーブル構成、正規化は第3正規形まで
- **過剰設計を避ける**: キャッシュテーブル、ログテーブルは作らない
- **将来拡張性**: マルチバイク対応は最初から許容(motorcycle_idで紐付け)

## ER図(テキスト表記)
┌─────────────────────┐      ┌──────────────────────────┐
│  motorcycles        │      │  maintenance_records     │
├─────────────────────┤      ├──────────────────────────┤
│ id (PK)             │◄─────│ id (PK)                  │
│ name                │  1:N │ motorcycle_id (FK)       │
│ front_sprocket      │      │ performed_at             │
│ rear_sprocket       │      │ odometer_km              │
│ chain_links         │      │ lubricant                │
│ tire_circumference  │      │ notes                    │
│ created_at          │      │ created_at               │
│ updated_at          │      └──────────────────────────┘
└─────────────────────┘

## テーブル定義

### motorcycles

バイク情報を保持する。自分所有の1台を想定するが、構造上は複数対応可能。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | SERIAL | PRIMARY KEY | 自動採番 |
| name | VARCHAR(100) | NOT NULL | 車種名(例: "MT-09 SP") |
| front_sprocket | INT | NOT NULL, CHECK (front_sprocket > 0) | 前スプロケ丁数 |
| rear_sprocket | INT | NOT NULL, CHECK (rear_sprocket > 0) | 後スプロケ丁数 |
| chain_links | INT | NOT NULL, CHECK (chain_links > 0) | チェーンコマ数 |
| tire_circumference_mm | INT | NOT NULL, CHECK (tire_circumference_mm > 0) | リアタイヤ円周(mm) |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL DEFAULT NOW() | 作成日時 |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL DEFAULT NOW() | 更新日時 |

### maintenance_records

メンテナンス実施記録。motorcyclesに対してN:1。

| カラム | 型 | 制約 | 説明 |
|---|---|---|---|
| id | SERIAL | PRIMARY KEY | 自動採番 |
| motorcycle_id | INT | NOT NULL, FOREIGN KEY REFERENCES motorcycles(id) ON DELETE CASCADE | バイクID |
| performed_at | DATE | NOT NULL | メンテ実施日 |
| odometer_km | INT | NOT NULL, CHECK (odometer_km >= 0) | メンテ時点の走行距離(km) |
| lubricant | VARCHAR(100) | NULL可 | 使用ルブ銘柄 |
| notes | TEXT | NULL可 | 自由記述メモ |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL DEFAULT NOW() | 作成日時 |

## インデックス戦略

```sql
-- メンテ履歴の時系列取得を高速化
CREATE INDEX idx_maintenance_records_motorcycle_performed
    ON maintenance_records(motorcycle_id, performed_at DESC);
```

**判断根拠**: 履歴一覧の主要クエリは「特定バイクの最新メンテから降順」。
このクエリが頻発する想定のため複合インデックスを張る。
motorcyclesは数件しか入らない前提なので追加インデックス不要。

## マイグレーション戦略

- **Alembic**でバージョン管理
- 各マイグレーションは**1機能1ファイル**
- 本番(Aurora)への適用はCI/CD経由のみ、手動で直接SQL実行はしない
- ロールバックスクリプトは必ず書く(downgrade実装)

## 初期データ投入

```sql
-- MT-09 SP(2022-2024モデル純正想定値)
INSERT INTO motorcycles (name, front_sprocket, rear_sprocket, chain_links, tire_circumference_mm)
VALUES ('MT-09 SP', 16, 45, 118, 1992);
```

**注意**: 上記の数値は設計サンプル。実際にアプリ使用時は自分のバイクの実測値・
整備手帳の値を入力すること。この初期データは動作確認用のSeedに留める。

## 制約事項・既知の限界

- **時刻のタイムゾーン**: `TIMESTAMP WITH TIME ZONE`で統一、アプリ側はUTC管理、表示時のみJST変換
- **削除ポリシー**: 物理削除のみ(論理削除は実装しない、学習スコープ外)
- **同時編集**: 楽観ロック未実装(単一ユーザー前提のため不要)
