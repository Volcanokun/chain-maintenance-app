# CLAUDE.md — chain-maintenance-app

## コミット前チェックリスト（必須）

コミットを作成する前に、以下を**この順序で**必ず実行すること。

```bash
uv run ruff check .        # lint
uv run pytest tests/ -v    # テスト
uv run alembic upgrade head # マイグレーション（デプロイ時にしか検知できないバグを早期発見するため）
```

3つすべてが成功してからコミットする。

## プロジェクト概要

バイクスペック検索 API。FastAPI + Aurora Serverless v2 (PostgreSQL) を ECS Fargate で運用。

## 技術スタック

- **アプリ**: Python 3.12 / FastAPI / SQLAlchemy / Alembic
- **インフラ**: AWS (ECS Fargate / ALB / Aurora Serverless v2 / ECR) / Terraform
- **CI/CD**: GitHub Actions (OIDC認証)
- **パッケージ管理**: uv
- **ローカル DB**: SQLite（`dev.db`）/ 本番は PostgreSQL

## ローカル開発の注意点

- ローカルは SQLite にフォールバックするため、Alembic マイグレーションは**SQLite でも動く**書き方が必要
  - `op.create_unique_constraint()` 等の ALTER TABLE 系は `op.batch_alter_table()` でラップする
  - upsert は `ON CONFLICT(col, col)` 構文（SQLite 3.24+ / PostgreSQL 両対応）を使う。`ON CONFLICT ON CONSTRAINT name` は PostgreSQL 専用なので使わない
- `XRAY_ENABLED` 環境変数が未設定の場合、X-Ray は無効（ローカルでは daemon が存在しないため）

## インフラ

```
infra/
├── main.tf          # プロバイダー設定
├── variables.tf     # 変数定義
├── vpc.tf           # VPC / サブネット / SG / VPC Endpoint
├── ecr.tf           # ECR（IMMUTABLEタグ）
├── aurora.tf        # Aurora Serverless v2 + Secrets Manager
├── alb.tf           # ALB + ターゲットグループ
├── dns.tf           # Cloudflare DNS + ACM（git管理外）
├── ecs.tf           # ECS Fargate + IAM + Auto Scaling
├── github_actions.tf# OIDC + GitHub Actions IAMロール
└── cloudtrail.tf    # 監査ログ
```

## Phase 進捗

| Phase | 内容 | 状態 |
|---|---|---|
| Phase 1-4 | FastAPI / AWS / HTTPS / フロントエンド / セキュリティ | ✅ 完了 |
| Phase 5-A | X-Ray 分散トレーシング | 🚧 実装中 |
| Phase 5-B | CodeDeploy Blue/Green デプロイ | 📋 予定 |
