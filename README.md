# Chain Maintenance App

バイクのチェーンメンテナンス記録Webアプリ。
**AWS上でRDS・HTTPS・Auto Scalingを実地検証するための学習プロジェクト**として構築。

## プロジェクトの目的

プロダクトとしての目的ではなく、**技術検証を主目的**としたプロジェクトです。
ただし「動くだけ」で終わらせず、以下を重視しています:

- アーキ図・選定理由・コスト試算をドキュメントで可視化
- 本番相当の構成(HTTPS、Secrets Manager、Auto Scaling)を個人スケールで再現
- コスト意識(月5,000円以下の学習台)を設計に反映

## アーキテクチャ概要
[User] → [Route53] → [ALB(HTTPS)] → [ECS Fargate(FastAPI)] → [Aurora Serverless v2]
↓
[VPC Endpoints: ECR, Secrets Manager, Logs, S3]

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
- **フロントエンド**: HTML + Alpine.js(最小構成)
- **インフラ**: AWS ECS Fargate / Aurora Serverless v2 / ALB / VPC Endpoints
- **IaC**: Terraform
- **CI/CD**: GitHub Actions(OIDC認証)

## 開発フェーズ

| Phase | 内容 | 状態 |
|---|---|---|
| 0 | 設計(要件・スキーマ・アーキ・コスト) | 完了 |
| 1 | アプリ本体実装(ローカルSQLite動作) | 未着手 |
| 2 | RDS統合(Aurora Serverless v2) | 未着手 |
| 3 | HTTPS化(ACM + Route53) | 未着手 |
| 4 | Auto Scaling + 負荷試験 | 未着手 |

## セキュリティ対策

- pre-commit hook (git-secrets) によるAWS認証情報の誤コミット防止
- GitHub Dependabot alerts / security updates 有効化
- `.gitignore`で`.env`, `*.pem`, `.terraform/`等を追跡除外
- Branch protection rule(main直push禁止、PR必須)
- Phase 2以降: AWS Secrets Manager、OIDC認証でIAMアクセスキー発行なし

## 補足: 計算ロジック

チェーン1周にかかるホイール回転数:
回転数 = チェーンコマ数 / (リアスプロケ丁数 × 2)

例) MT-09 SP(リアスプロケ45T、チェーン118L)の場合:
`118 / (45 × 2) ≈ 1.31 回転`

→ リアタイヤのエアバルブを基準に、**約1周と1/3 回したらチェーン1周**。

## ライセンス

MIT(個人学習プロジェクト)
