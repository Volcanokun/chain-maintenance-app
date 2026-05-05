locals {
  name_prefix = "${var.project}-${var.environment}"
}

# ── VPC ──────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true # VPC Endpoint の名前解決に必須

  tags = { Name = "${local.name_prefix}-vpc" }
}

# ── サブネット ────────────────────────────────────────────────────────────────

resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  # ALBのみ配置するためパブリックIPは付与しない（ALBは明示的にIPを割り当て済み）
  map_public_ip_on_launch = false

  tags = { Name = "${local.name_prefix}-public-${var.availability_zones[count.index]}" }
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = { Name = "${local.name_prefix}-private-${var.availability_zones[count.index]}" }
}

# ── インターネットゲートウェイ（パブリックサブネット用）────────────────────

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-igw" }
}

# ── ルートテーブル ────────────────────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name_prefix}-rtb-public" }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# プライベートサブネットは NAT Gateway なし。
# インターネットへの経路は持たず、すべての AWS サービス通信は VPC Endpoint 経由。
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-rtb-private" }
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ── セキュリティグループ（ルールなしで先に作成し循環依存を回避）────────────

resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-sg-alb"
  description = "ALB: HTTPS inbound from Internet"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-alb" }
}

resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-sg-ecs"
  description = "ECS Fargate tasks"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-ecs" }
}

resource "aws_security_group" "rds" {
  name        = "${local.name_prefix}-sg-rds"
  description = "Aurora Serverless v2"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-rds" }
}

resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.name_prefix}-sg-vpce"
  description = "Interface VPC Endpoints (ECR / Secrets Manager / CloudWatch Logs)"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name_prefix}-sg-vpce" }
}

# ── セキュリティグループルール（SG作成後に別リソースで定義）─────────────────

# ALB inbound
resource "aws_security_group_rule" "alb_ingress_https" {
  security_group_id = aws_security_group.alb.id
  type              = "ingress"
  description       = "HTTPS from Internet"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "alb_ingress_http" {
  security_group_id = aws_security_group.alb.id
  type              = "ingress"
  description       = "HTTP redirect from Internet"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

# CodeDeploy Blue/Green テストリスナー（Green タスクの動作確認用）
resource "aws_security_group_rule" "alb_ingress_test" {
  security_group_id = aws_security_group.alb.id
  type              = "ingress"
  description       = "Test listener for CodeDeploy Blue/Green validation"
  from_port         = 8080
  to_port           = 8080
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

# ALB outbound → ECS
resource "aws_security_group_rule" "alb_egress_ecs" {
  security_group_id        = aws_security_group.alb.id
  type                     = "egress"
  description              = "Forward to ECS"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id
}

# ECS inbound ← ALB
resource "aws_security_group_rule" "ecs_ingress_alb" {
  security_group_id        = aws_security_group.ecs.id
  type                     = "ingress"
  description              = "From ALB"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
}

# ECS outbound → Aurora
resource "aws_security_group_rule" "ecs_egress_rds" {
  security_group_id        = aws_security_group.ecs.id
  type                     = "egress"
  description              = "To Aurora"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds.id
}

# ECS outbound → Interface VPC Endpoints
resource "aws_security_group_rule" "ecs_egress_vpce" {
  security_group_id        = aws_security_group.ecs.id
  type                     = "egress"
  description              = "To VPC Endpoints (ECR / Secrets Manager / CloudWatch Logs)"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpc_endpoints.id
}

# ECS outbound → S3 Gateway Endpoint（プレフィックスリスト経由）
resource "aws_security_group_rule" "ecs_egress_s3" {
  security_group_id = aws_security_group.ecs.id
  type              = "egress"
  description       = "To S3 Gateway Endpoint"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  prefix_list_ids   = [aws_vpc_endpoint.s3.prefix_list_id]
}

# RDS inbound ← ECS
resource "aws_security_group_rule" "rds_ingress_ecs" {
  security_group_id        = aws_security_group.rds.id
  type                     = "ingress"
  description              = "PostgreSQL from ECS"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id
}

# VPC Endpoints inbound ← ECS
resource "aws_security_group_rule" "vpce_ingress_ecs" {
  security_group_id        = aws_security_group.vpc_endpoints.id
  type                     = "ingress"
  description              = "HTTPS from ECS"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id
}

# ── VPC Endpoints ─────────────────────────────────────────────────────────────

# ECR (イメージ manifest / API 操作)
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${local.name_prefix}-vpce-ecr-api" }
}

# ECR (イメージレイヤー取得: Docker デーモン通信)
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${local.name_prefix}-vpce-ecr-dkr" }
}

# S3 Gateway (ECR イメージレイヤーの実体は S3 に保存されているため必須、無料)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = { Name = "${local.name_prefix}-vpce-s3" }
}

# Secrets Manager (DB 認証情報取得)
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${local.name_prefix}-vpce-secretsmanager" }
}

# CloudWatch Logs (ECS コンテナログ出力)
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${local.name_prefix}-vpce-logs" }
}

# X-Ray (xray-daemon サイドカーがトレースデータを送信)
resource "aws_vpc_endpoint" "xray" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.xray"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${local.name_prefix}-vpce-xray" }
}
