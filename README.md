# Bike Specs Lookup App (旧: Chain Maintenance App)

バイクのスペック情報（排気量・チェーン・スプロケット）を検索できるWebアプリ。
**AWS上でRDS・HTTPS・Auto Scalingを実地検証するための学習プロジェクト**として構築。

## プロジェクトの目的

プロダクトとしての目的ではなく、**技術検証を主目的**としたプロジェクトです。
ただし「動くだけ」で終わらせず、以下を重視しています:

- アーキ図・選定理由・コスト試算をドキュメントで可視化
- 本番相当の構成(HTTPS、Secrets Manager、Auto Scaling)を個人スケールで再現
- コスト意識(月5,000円以下の学習台)を設計に反映

## アーキテクチャ概要
```
[User] → [Cloudflare DNS] → [ALB(HTTPS/443)] → [ECS Fargate(FastAPI)] → [Aurora Serverless v2]
                                                          ↓
                                         [VPC Endpoints: ECR, Secrets Manager, Logs, S3]
```

詳細は [docs/architecture.md](./docs/architecture.md) 参照。

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/requirements.md](./docs/requirements.md) | 機能要件・非機能要件 |
| [docs/schema.md](./docs/schema.md) | DBスキーマ設計 |
| [docs/architecture.md](./docs/architecture.md) | AWSアーキテクチャ設計 |
| [docs/cost-estimate.md](./docs/cost-estimate.md) | 月額コスト試算 |

## 技術スタック

- **バックエンド**: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic
- **フロントエンド**: HTML + Alpine.js + Tailwind CSS
- **データ**: Bike Masters スクレイパー（排気量・チェーン・スプロケ情報）
- **インフラ**: AWS ECS Fargate / Aurora Serverless v2 / ALB / VPC Endpoints
- **DNS**: Cloudflare + ACM（chain-app.volcanokun.dev）
- **IaC**: Terraform
- **CI/CD**: GitHub Actions（OIDC認証、IAMアクセスキー不使用）
- **パッケージ管理**: uv

## 開発フェーズ

| Phase | 内容 | 状態 |
|---|---|---|
| 0 | 設計（要件・スキーマ・アーキ・コスト） | ✅ 完了 |
| 1 | アプリ本体実装（FastAPI + SQLAlchemy、ローカルSQLite動作） | ✅ 完了 |
| 2 | AWSインフラ構築（ECS Fargate + Aurora Serverless v2 + ALB + VPC Endpoint） | ✅ 完了 |
| 3-A | HTTPS化（ACM + Cloudflare DNS）+ Auto Scaling + Locust負荷試験 | ✅ 完了 |
| 3-B | アプリピボット（バイクスペック検索サービス）+ フロントエンド実装 | ✅ 完了 |
| 3-B+ | 排気量フィルタ・UIリデザイン・Bike Mastersスクレイパー追加 | ✅ 完了 |

## セキュリティ対策

- **gitleaks pre-commit hook**（`.pre-commit-config.yaml`）によるシークレット誤コミット防止
- GitHub Dependabot alerts / security updates 有効化
- `.gitignore`で`.env`, `*.pem`, `.terraform/`等を追跡除外
- Branch protection rule（main直push禁止、PR必須）
- AWS Secrets Manager でDB認証情報を管理（コードにハードコードなし）
- GitHub Actions OIDC認証でIAMアクセスキー発行なし
- ECS/GitHub ActionsのIAMロールは最小権限ポリシー
- CloudTrail による API 操作ログ記録（90日保持）

## ライセンス

MIT(個人学習プロジェクト)
