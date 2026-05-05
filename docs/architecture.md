# アーキテクチャ設計 - Bike Specs Lookup App

## フェーズ進捗

| フェーズ | 内容 | 状態 |
|---|---|---|
| Phase 1 | FastAPI アプリ実装・ローカル動作確認 | ✅ 完了 |
| Phase 2 | AWSインフラ構築・CI/CD・本番デプロイ | ✅ 完了 |
| Phase 3-A | HTTPS化（ACM + Cloudflare DNS）・Auto Scaling・Locust負荷試験 | ✅ 完了 |
| Phase 3-B | アプリピボット（バイクスペック検索）・フロントエンド実装 | ✅ 完了 |
| Phase 3-B+ | 排気量フィルタ・全メーカーCSVシード・セキュリティ強化 | ✅ 完了 |

## 全体構成図

```
                     ┌─────────────────────┐
                     │   ユーザーブラウザ   │
                     └──────────┬──────────┘
                                │ HTTPS (443)
                                ▼
                     ┌─────────────────────┐
                     │   Cloudflare DNS    │
                     │ chain-app.          │
                     │ volcanokun.dev      │
                     └──────────┬──────────┘
                                │ CNAME → ALB
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16)                                                    │
│                                                                       │
│  ┌─── Public Subnet × 2AZ ──────────────────────────────────────┐   │
│  │                                                                │   │
│  │         ┌─────────────────────────────────────┐               │   │
│  │         │  Application Load Balancer (ALB)    │               │   │
│  │         │  - 80→443 リダイレクト              │               │   │
│  │         │  - HTTPS終端（ACM証明書）           │               │   │
│  │         └──────────────┬──────────────────────┘               │   │
│  │                        │                                       │   │
│  └────────────────────────┼───────────────────────────────────────┘   │
│                           │                                           │
│  ┌─── Private Subnet × 2AZ ─────────────────────────────────────┐   │
│  │                        ▼                                      │   │
│  │         ┌─────────────────────────────────────┐              │   │
│  │         │  ECS Fargate Service                │              │   │
│  │         │  - FastAPI コンテナ                 │              │   │
│  │         │  - xray-daemon サイドカー           │              │   │
│  │         │  - タスク数: 1〜4（Auto Scaling）   │              │   │
│  │         │  - CPU: 0.25 vCPU / Memory: 0.5 GB  │              │   │
│  │         └────┬──────────────────────┬──────────┘              │   │
│  │              │                      │                          │   │
│  │    VPC Endpoint経由       VPC Endpoint経由                    │   │
│  │              ▼                      ▼                          │   │
│  │         ┌──────────┐          ┌──────────┐                   │   │
│  │         │   ECR    │          │ Secrets  │                   │   │
│  │         │(dkr/api) │          │  Manager │                   │   │
│  │         └──────────┘          └─────┬────┘                   │   │
│  │                                     │ DB認証情報取得          │   │
│  │                                     ▼                          │   │
│  │         ┌─────────────────────────────────────┐              │   │
│  │         │  Aurora Serverless v2 PostgreSQL    │              │   │
│  │         │  - 最小 0 ACU / 最大 1 ACU          │              │   │
│  │         │  - Auto Pause 有効                  │              │   │
│  │         │  - SSL強制（rds.force_ssl=1）        │              │   │
│  │         └─────────────────────────────────────┘              │   │
│  │                                                               │   │
│  │         ┌─────────────────────────────────────┐              │   │
│  │         │  CloudWatch Logs VPC Endpoint       │              │   │
│  │         └─────────────────────────────────────┘              │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│         ┌─────────────────────────────────────┐                      │
│         │  CloudTrail → S3バケット             │                      │
│         │  （API操作ログ 90日保持）             │                      │
│         └─────────────────────────────────────┘                      │
└───────────────────────────────────────────────────────────────────────┘
                ┌──────────────────────────────┐
                │  GitHub Actions (CI/CD)      │
                │  - buildx → ECR push         │
                │  - Alembic migration実行     │
                │  - ECS Service更新           │
                └──────────────────────────────┘
```

## 技術選定と却下理由

### コンピュート層

| 選定 | 採用 | 理由 |
|---|---|---|
| **ECS Fargate** | 採用 | EC2管理不要、既存基盤流用可、コンテナ知識活かせる |
| Lambda | 却下 | コールドスタート・15分制限があり学習対象として劣る |
| EC2 | 却下 | OS管理の学習価値はあるが、今回のスコープ外 |
| App Runner | 却下 | 簡単すぎてVPC設計・Auto Scalingの学習機会が減る |

### データベース層

| 選定 | 採用 | 理由 |
|---|---|---|
| **Aurora Serverless v2 (PostgreSQL)** | 採用 | 0 ACU対応で未使用時課金なし、学習コスト圧縮 |
| RDS（通常インスタンス） | 却下 | 停止してもストレージ・スナップショット課金継続 |
| DynamoDB | 却下 | リレーション表現が不得手、SQLの学習機会減 |
| Aurora Serverless v1 | 却下 | v2より機能制約多く、新規採用非推奨 |

### ネットワーク層

| 選定 | 採用 | 理由 |
|---|---|---|
| **VPC Endpoint（Interface型）** | 採用 | NAT Gateway回避、コスト意識を設計で示せる |
| NAT Gateway | 却下 | 月5,000円強、学習台としてはオーバーコスト |
| パブリックサブネット直置き | 却下 | セキュリティ上のアンチパターン |

**VPC Endpoint採用サービス**:
- `ecr.dkr`（Interface）
- `ecr.api`（Interface）
- `s3`（Gateway、無料、ECRイメージレイヤー取得用）
- `secretsmanager`（Interface）
- `logs`（Interface、CloudWatch Logs用）

### DNS層

| 選定 | 採用 | 理由 |
|---|---|---|
| **Cloudflare DNS** | 採用 | 無料、既存ドメイン（volcanokun.dev）で運用済み |
| Route 53 | 却下 | ホストゾーン月$0.5 + クエリ課金、Cloudflareで代替可能 |

### ロードバランサ層

| 選定 | 採用 | 理由 |
|---|---|---|
| **ALB** | 採用 | HTTPS終端、パスベースルーティング拡張余地 |
| NLB | 却下 | L4のみ、HTTPS終端・リダイレクト機能なし |

### アプリケーションフレームワーク

| 選定 | 採用 | 理由 |
|---|---|---|
| **FastAPI** | 採用 | 型ヒント + Swagger UI自動生成、面談時の「動くAPIドキュメント」として即戦力 |
| Flask/Quart | 却下 | 過去の個人プロジェクトで使用済み、学習メリット薄 |
| Django | 却下 | 今回の規模に対して過剰 |

## セキュリティ設計

### セキュリティグループ階層

```
[ALB-SG]
  Inbound : 0.0.0.0/0 から 443（および 80→443 リダイレクト）
  Outbound: ECS-SG へ 8000

[ECS-SG]
  Inbound : ALB-SG から 8000
  Outbound: RDS-SG へ 5432、VPC-Endpoints-SG へ 443

[RDS-SG]
  Inbound : ECS-SG から 5432
  Outbound: なし

[VPC-Endpoints-SG]
  Inbound : ECS-SG から 443
  Outbound: なし
```

**原則**: 最小権限・送信元はSG ID参照（CIDR参照しない）

### 認証情報管理

- DB接続情報は **Secrets Manager** で管理
- ECSタスクロール経由でアプリ起動時に取得
- `.env`ファイルや環境変数への直接記載は **禁止**
- GitHub Actionsの認証は **OIDC**（IAMアクセスキー発行しない）
- IAMロールは最小権限ポリシー（ECSロール・GitHub Actionsロールともにwildcard `*` 不使用、秘密情報へのアクセスは特定ARNのみ）

### シークレット誤コミット防止

- `gitleaks` pre-commitフック（`.pre-commit-config.yaml`）
- `ruff` pre-commitフック（lint）
- `data/` ディレクトリのCSVファイルにシークレット相当情報を含めない

### 通信暗号化

- **外部 → ALB**: HTTPS（ACM証明書、TLS 1.2以上）
- **ALB → ECS**: HTTP（VPC内部、HSTSヘッダ付与）
- **ECS → Aurora**: SSL強制（`rds.force_ssl=1` パラメータグループ）
- **ECS → VPC Endpoint**: HTTPS自動

### 監査ログ

- **CloudTrail**: 全APIコール記録（IAMグローバルイベント含む）
- ログはS3バケットに90日保持
- ログ改ざん検知有効（`enable_log_file_validation = true`）

## CI/CD設計

### パイプライン構成（GitHub Actions）

```
[Push to main / workflow_dispatch]
        ↓
[Lint & Test] (ruff check / pytest)
        ↓
[Docker Build] (buildx, linux/amd64, multi-stage)
        ↓
[ECR Push] (OIDC認証, shaタグ)
        ↓
[Alembic Migration] (ECS Run Task)
        ↓
[CodeDeploy Blue/Green]
  - AppSpec JSON を動的生成
  - aws deploy create-deployment
  - Green タスク起動 → テストリスナー(8080)で確認
  - 本番リスナー(443)を Blue→Green に切替
  - 5分後に Blue タスクを終了
        ↓
[aws deploy wait deployment-successful]
```

**ポイント**: Migration → Deploy の順序を守る。逆にすると新コードが古いスキーマを叩いて落ちる。

### 重要な実装メモ

- ECR は `IMMUTABLE` タグのため `sha` タグのみ使用（`latest` 上書き不可）
- Alembicは `python -m alembic` で実行（multi-stage buildでシバンパスが変わるため）
- `deploy` ジョブの `needs` に `build` と `migrate` の両方が必要（出力参照のため）
- DB接続は `DB_HOST` 等の個別env vars → `config.py` の `model_validator` でPostgreSQL URLを組み立て

## インフラ構成ファイル

```
infra/
├── main.tf            # AWS / random / Cloudflare プロバイダー設定
├── variables.tf       # 変数定義（リージョン・CIDR・AZ等）
├── terraform.tfvars   # 変数値（git管理外）
├── outputs.tf         # 出力値（ALB DNS名・ECR URL・IAMロールARN等）
├── vpc.tf             # VPC / サブネット / SG / VPC Endpoint
├── ecr.tf             # ECR リポジトリ（IMMUTABLE・ライフサイクルポリシー）
├── aurora.tf          # Aurora Serverless v2 + Secrets Manager
├── alb.tf             # ALB + ターゲットグループ + HTTPリスナー（→443リダイレクト）
├── dns.tf             # Cloudflare DNS + ACM証明書（git管理外）
├── ecs.tf             # ECS Fargate + IAM ロール + Auto Scaling
├── github_actions.tf  # OIDC プロバイダー + GitHub Actions IAM ロール
└── cloudtrail.tf      # CloudTrail + S3バケット（監査ログ90日保持）
```

## DB接続設定

ECS が Secrets Manager から以下を個別注入:

```
DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
```

`app/core/config.py` の `model_validator` が PostgreSQL URL に変換:

```
postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require
```

ローカル開発時は `DB_HOST` 未設定 → SQLite（`sqlite:///./dev.db`）にフォールバック。

## 監視・ログ設計

| 観点 | 設定 |
|---|---|
| アプリログ | ECS → CloudWatch Logs（VPC Endpoint経由）、30日保持 |
| 監査ログ | CloudTrail → S3、90日保持、ログ改ざん検知あり |
| メトリクス | CloudWatch標準（ECS CPU・ALB 4xx/5xx・Aurora ACU） |
| コストアラート | 月$20（約3,000円）・月$53（約8,000円）でメール通知 |
| 分散トレーシング | X-Ray（xray-daemon サイドカー + aws-xray-sdk）|

## 障害対応設計

| 故障点 | 影響 | 対応 |
|---|---|---|
| ECSタスク1つが落ちる | なし | Auto Scalingで自動復旧 |
| AZ全体障害 | 一時的に劣化 | もう1AZで継続、タスク復旧 |
| Aurora停止（ACU 0状態からの起動） | 初回リクエスト遅延約15秒 | アプリ側でリトライ実装、30秒タイムアウト |
| ALBヘルスチェック失敗 | タスク入れ替え | `/health`エンドポイントで対応 |

## 制約事項・既知の課題

- **単一リージョン構成**: ap-northeast-1のみ、DR考慮なし（学習スコープ外）
- **バックアップ**: Aurora自動バックアップ（1日保持）のみ
- **WAF**: 未導入（学習終了後はALBを停止して対応）
- **Aurora接続プール枯渇**: 高負荷時に接続プールが先にボトルネックになり、CPUスケーリングが発火しない（RDS Proxy導入で解決可能）
- **tfstate管理**: 現在ローカル管理。チーム開発時はS3バックエンドに移行する（main.tfにコメントアウト済み）
- **VPC Endpointコスト**: Interface型4本×2AZ≒$81/月。長期運用時は停止スクリプトで対応
