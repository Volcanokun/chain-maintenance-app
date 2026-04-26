# ── VPC ──────────────────────────────────────────────────────────────────────

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR ブロック"
  value       = aws_vpc.main.cidr_block
}

# ── サブネット ────────────────────────────────────────────────────────────────

output "public_subnet_ids" {
  description = "パブリックサブネット ID 一覧（ALB 配置用）"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "プライベートサブネット ID 一覧（ECS / Aurora 配置用）"
  value       = aws_subnet.private[*].id
}

# ── セキュリティグループ ──────────────────────────────────────────────────────

output "sg_alb_id" {
  description = "ALB セキュリティグループ ID"
  value       = aws_security_group.alb.id
}

output "sg_ecs_id" {
  description = "ECS セキュリティグループ ID"
  value       = aws_security_group.ecs.id
}

output "sg_rds_id" {
  description = "RDS (Aurora) セキュリティグループ ID"
  value       = aws_security_group.rds.id
}

output "sg_vpc_endpoints_id" {
  description = "VPC Endpoints セキュリティグループ ID"
  value       = aws_security_group.vpc_endpoints.id
}

# ── VPC Endpoints ─────────────────────────────────────────────────────────────

output "vpce_ecr_api_id" {
  description = "ECR API VPC Endpoint ID"
  value       = aws_vpc_endpoint.ecr_api.id
}

output "vpce_ecr_dkr_id" {
  description = "ECR DKR VPC Endpoint ID"
  value       = aws_vpc_endpoint.ecr_dkr.id
}

output "vpce_s3_id" {
  description = "S3 Gateway VPC Endpoint ID"
  value       = aws_vpc_endpoint.s3.id
}

output "vpce_secretsmanager_id" {
  description = "Secrets Manager VPC Endpoint ID"
  value       = aws_vpc_endpoint.secretsmanager.id
}

output "vpce_logs_id" {
  description = "CloudWatch Logs VPC Endpoint ID"
  value       = aws_vpc_endpoint.logs.id
}

# ── ルートテーブル ────────────────────────────────────────────────────────────

output "private_route_table_id" {
  description = "プライベートサブネット用ルートテーブル ID（他リソースの Endpoint アタッチ時に使用）"
  value       = aws_route_table.private.id
}

# ── ECR ──────────────────────────────────────────────────────────────────────

output "ecr_repository_url" {
  description = "ECR リポジトリ URL（docker push / CI/CD のイメージプッシュ先）"
  value       = aws_ecr_repository.app.repository_url
}

# ── Aurora ───────────────────────────────────────────────────────────────────

output "db_cluster_endpoint" {
  description = "Aurora クラスターエンドポイント（書き込み用）"
  value       = aws_rds_cluster.main.endpoint
}

output "db_secret_arn" {
  description = "DB 認証情報の Secrets Manager ARN"
  value       = aws_secretsmanager_secret.db.arn
}

# ── ALB ──────────────────────────────────────────────────────────────────────

output "alb_dns_name" {
  description = "ALB の DNS 名（ブラウザアクセス用: http://<この値>）"
  value       = aws_lb.main.dns_name
}

# ── ECS ──────────────────────────────────────────────────────────────────────

output "ecs_cluster_name" {
  description = "ECS クラスター名（CI/CD の force-new-deployment 等で使用）"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS サービス名"
  value       = aws_ecs_service.app.name
}

# ── GitHub Actions ────────────────────────────────────────────────────────────

output "aws_account_id" {
  description = "AWS アカウント ID（github_actions.tf の data.aws_caller_identity から取得）"
  value       = data.aws_caller_identity.current.account_id
}

output "github_actions_role_arn" {
  description = "GitHub Actions が AssumeRole する IAM ロール ARN（GitHub Secret: AWS_ROLE_ARN に設定する）"
  value       = aws_iam_role.github_actions.arn
}
