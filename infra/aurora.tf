variable "aurora_engine_version" {
  description = "Aurora PostgreSQL エンジンバージョン（aws rds describe-db-engine-versions で確認）"
  type        = string
  default     = "16.6"
}

# ── DB パスワード生成 ─────────────────────────────────────────────────────────

resource "random_password" "db" {
  length  = 32
  special = false # Aurora は一部の記号を許可しないため英数字のみ
}

# ── Secrets Manager ───────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "db" {
  name = "${local.name_prefix}/db/credentials"

  # 学習環境のため即時削除を許可（本番では 7〜30 日に変更）
  recovery_window_in_days = 0

  tags = { Name = "${local.name_prefix}-db-secret" }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id

  secret_string = jsonencode({
    username = "dbadmin"
    password = random_password.db.result
    dbname   = "chain_maintenance"
    host     = aws_rds_cluster.main.endpoint
    port     = 5432
  })
}

# ── DB サブネットグループ ──────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${local.name_prefix}-db-subnet-group" }
}

# ── クラスターパラメータグループ（SSL 強制）────────────────────────────────────

resource "aws_rds_cluster_parameter_group" "main" {
  name   = "${local.name_prefix}-cluster-pg"
  family = "aurora-postgresql16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = { Name = "${local.name_prefix}-cluster-pg" }
}

# ── Aurora Serverless v2 クラスター ───────────────────────────────────────────

resource "aws_rds_cluster" "main" {
  cluster_identifier              = "${local.name_prefix}-cluster"
  engine                          = "aurora-postgresql"
  engine_mode                     = "provisioned"
  engine_version                  = var.aurora_engine_version
  database_name                   = "chain_maintenance"
  master_username                 = "dbadmin"
  master_password                 = random_password.db.result
  db_subnet_group_name            = aws_db_subnet_group.main.name
  vpc_security_group_ids          = [aws_security_group.rds.id]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.main.name
  storage_encrypted               = true
  backup_retention_period         = 1
  skip_final_snapshot             = true
  deletion_protection             = false

  # min_capacity = 0 で AutoPause 有効（未使用時に 0 ACU へスケールダウン）
  serverlessv2_scaling_configuration {
    min_capacity = 0
    max_capacity = 1
  }

  tags = { Name = "${local.name_prefix}-cluster" }
}

# ── Aurora Serverless v2 インスタンス ─────────────────────────────────────────

resource "aws_rds_cluster_instance" "main" {
  identifier           = "${local.name_prefix}-instance-1"
  cluster_identifier   = aws_rds_cluster.main.id
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.main.engine
  engine_version       = aws_rds_cluster.main.engine_version
  db_subnet_group_name = aws_db_subnet_group.main.name

  performance_insights_enabled = false

  tags = { Name = "${local.name_prefix}-instance-1" }
}
