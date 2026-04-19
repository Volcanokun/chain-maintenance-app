# アーキテクチャ設計 - Chain Maintenance App

## 全体構成図
                     ┌─────────────────────┐
                     │   ユーザーブラウザ   │
                     └──────────┬──────────┘
                                │ HTTPS (443)
                                ▼
                     ┌─────────────────────┐
                     │     Route 53        │
                     │ (ホストゾーン)      │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   ACM (証明書)      │
                     └──────────┬──────────┘
                                │
┌───────────────────────────────────┼──────────────────────────────────┐
│  VPC (10.0.0.0/16)                │                                   │
│                                    ▼                                   │
│  ┌─── Public Subnet × 2AZ ────────────────────────────────────┐     │
│  │                                                              │     │
│  │         ┌─────────────────────────────────────┐              │     │
│  │         │  Application Load Balancer (ALB)    │              │     │
│  │         │  - 80→443 リダイレクト              │              │     │
│  │         │  - HTTPS終端                        │              │     │
│  │         └──────────────┬──────────────────────┘              │     │
│  │                        │                                      │     │
│  └────────────────────────┼──────────────────────────────────────┘     │
│                           │                                            │
│  ┌─── Private Subnet × 2AZ ──────────────────────────────────────┐   │
│  │                        ▼                                       │   │
│  │         ┌─────────────────────────────────────┐               │   │
│  │         │  ECS Fargate Service                │               │   │
│  │         │  - FastAPI コンテナ                 │               │   │
│  │         │  - タスク数: 1〜4(Auto Scaling)   │               │   │
│  │         │  - CPU: 0.25 vCPU / Memory: 0.5 GB  │               │   │
│  │         └────┬──────────────────────┬─────────┘               │   │
│  │              │                      │                          │   │
│  │              │ VPC Endpoint経由     │ VPC Endpoint経由         │   │
│  │              ▼                      ▼                          │   │
│  │         ┌──────────┐          ┌──────────┐                    │   │
│  │         │   ECR    │          │ Secrets  │                    │   │
│  │         │(Interface│          │  Manager │                    │   │
│  │         │ Endpoint)│          │(Interface│                    │   │
│  │         └──────────┘          │ Endpoint)│                    │   │
│  │                               └─────┬────┘                    │   │
│  │                                     │ DB認証情報取得          │   │
│  │                                     ▼                          │   │
│  │         ┌─────────────────────────────────────┐               │   │
│  │         │  Aurora Serverless v2 PostgreSQL    │               │   │
│  │         │  - 最小 0 ACU / 最大 1 ACU          │               │   │
│  │         │  - Auto Pause 有効                  │               │   │
│  │         └─────────────────────────────────────┘               │   │
│  │                                                                │   │
│  │         ┌─────────────────────────────────────┐               │   │
│  │         │  CloudWatch Logs VPC Endpoint       │               │   │
│  │         │  (ECSログ出力用)                    │               │   │
│  │         └─────────────────────────────────────┘               │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                ┌──────────────────────────────┐
                │  GitHub Actions (CI/CD)      │
                │  - buildx → ECR push         │
                │  - ECS Service更新           │
                │  - Alembic migration実行     │
                └──────────────────────────────┘

## 技術選定と却下理由

### コンピュート層

| 選定 | 採用 | 理由 |
|---|---|---|
| **ECS Fargate** | 採用 | EC2管理不要、既存基盤流用可、コンテナ知識活かせる |
| Lambda | 却下 | ALBとの統合は可だが、コールドスタート・15分制限があり学習対象として劣る |
| EC2 | 却下 | OS管理の学習価値はあるが、今回のスコープ外 |
| App Runner | 却下 | 簡単すぎて「VPC設計・Auto Scaling」の学習機会が減る |

### データベース層

| 選定 | 採用 | 理由 |
|---|---|---|
| **Aurora Serverless v2 (PostgreSQL)** | 採用 | 0 ACU対応で未使用時課金なし、学習コスト圧縮 |
| RDS (通常インスタンス) | 却下 | 停止してもストレージ・スナップショット課金継続 |
| DynamoDB | 却下 | リレーション表現が不得手、SQLの学習機会減 |
| Aurora Serverless v1 | 却下 | v2より機能制約多く、新規採用非推奨 |

### ネットワーク層

| 選定 | 採用 | 理由 |
|---|---|---|
| **VPC Endpoint(Interface型)** | 採用 | NAT Gateway回避、コスト意識を設計で示せる |
| NAT Gateway | 却下 | 月5,000円強、学習台としてはオーバーコスト |
| パブリックサブネット直置き | 却下 | セキュリティ上のアンチパターン、ポートフォリオ価値低下 |

**VPC Endpoint採用サービス**:
- `com.amazonaws.ap-northeast-1.ecr.dkr`(Interface)
- `com.amazonaws.ap-northeast-1.ecr.api`(Interface)
- `com.amazonaws.ap-northeast-1.s3`(Gateway、無料、ECRイメージレイヤー取得用)
- `com.amazonaws.ap-northeast-1.secretsmanager`(Interface)
- `com.amazonaws.ap-northeast-1.logs`(Interface、CloudWatch Logs用)

### ロードバランサ層

| 選定 | 採用 | 理由 |
|---|---|---|
| **ALB** | 採用 | HTTPS終端、パスベースルーティング拡張余地 |
| CloudFront + S3 | 却下 | 動的API配信に不向き、API Gatewayと組み合わせも可だが構成が過度に複雑化 |
| NLB | 却下 | L4のみ、HTTPS終端・リダイレクト機能なし |

### アプリケーションフレームワーク

| 選定 | 採用 | 理由 |
|---|---|---|
| **FastAPI** | 採用 | 型ヒント + Swagger UI自動生成、面談時の「動くAPIドキュメント」として即戦力 |
| Flask/Quart | 却下 | 過去の個人プロジェクトで使用済み、学習メリット薄 |
| Django | 却下 | 今回の規模に対して過剰、管理画面も不要 |
| Spring Boot | 却下 | 職歴で十分示せる、あえて個人開発では採用しない |

## セキュリティ設計

### セキュリティグループ階層
[ALB-SG]
Inbound: 0.0.0.0/0 から 443
Outbound: ECS-SG へ 8000
[ECS-SG]
Inbound: ALB-SG から 8000
Outbound: RDS-SG へ 5432, VPC-Endpoints-SG へ 443
[RDS-SG]
Inbound: ECS-SG から 5432
Outbound: なし
[VPC-Endpoints-SG]
Inbound: ECS-SG から 443
Outbound: なし

**原則**: 最小権限・送信元はSG ID参照(CIDR参照しない)

### 認証情報管理

- DB接続情報は**Secrets Manager**で管理、**自動ローテーション有効化**
- アプリ起動時にECSタスクロール経由で取得
- `.env`ファイルや環境変数への直接記載は**禁止**
- GitHub Actionsの認証は**OIDC**(IAMアクセスキー発行しない)

### 通信暗号化

- **外部 → ALB**: HTTPS (ACM証明書、TLS 1.2以上)
- **ALB → ECS**: HTTPでも可(VPC内部)、ただしHSTSヘッダ付与
- **ECS → Aurora**: PostgreSQL接続にSSL強制(`sslmode=require`)
- **ECS → VPC Endpoint**: HTTPS自動

## CI/CD設計

### パイプライン構成(GitHub Actions)
[Push to main]
↓
[Lint & Test] (pytest, ruff)
↓
[Docker Build] (buildx, multi-stage)
↓
[ECR Push] (OIDC認証)
↓
[Alembic Migration] (ECS Run Task)
↓
[ECS Service Update] (force-new-deployment)
↓
[Health Check待機]

**ポイント**: Migration → Deploy の順序を守る。逆にすると新コードが古いスキーマを叩いて落ちる。

## 監視・ログ設計

- **ログ**: ECS → CloudWatch Logs(VPC Endpoint経由)
- **メトリクス**: CloudWatch標準メトリクス(ECS CPU、ALB 4xx/5xx、Aurora ACU)
- **アラーム**: 学習台のため**コストアラート**のみ設定(月3,000円超過で通知)
- **分散トレーシング**: 今回は未実装(X-Rayは学習スコープ外)

## 障害対応設計

| 故障点 | 影響 | 対応 |
|---|---|---|
| ECSタスク1つが落ちる | なし | Auto Scalingで自動復旧 |
| AZ全体障害 | 一時的に劣化 | もう1AZで継続、タスク復旧 |
| Aurora停止(ACU 0状態からの起動) | 初回リクエスト遅延 | アプリ側でリトライ実装、30秒タイムアウト |
| ALBヘルスチェック失敗 | タスク入れ替え | `/health`エンドポイント実装で対応 |

## 制約事項・既知の課題

- **単一リージョン構成**: ap-northeast-1のみ、DR考慮なし(学習スコープ外)
- **バックアップ**: Aurora自動バックアップ(1日保持)のみ
- **WAF**: 未導入、パブリックURL露出リスクあり(学習終了後はALBを停止して対応)
