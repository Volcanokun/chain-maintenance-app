variable "app_image_tag" {
  description = "デプロイする Docker イメージタグ（CI/CD から -var app_image_tag=<sha> で上書き）"
  type        = string
  default     = "latest"
}

# ── CloudWatch Logs ───────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 30

  tags = { Name = "${local.name_prefix}-ecs-logs" }
}

# ── IAM: 共通 Trust Policy ────────────────────────────────────────────────────

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# ── IAM: Task Execution Role（ECS エージェント用）────────────────────────────
# ECR イメージ pull・CloudWatch Logs 書き込み・シークレット注入に使用

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name_prefix}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json

  tags = { Name = "${local.name_prefix}-ecs-execution-role" }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-manager-read"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.db.arn]
    }]
  })
}

# ── IAM: Task Role（アプリコンテナ用）────────────────────────────────────────
# アプリ自身が起動後に Secrets Manager を読む場合に使用

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json

  tags = { Name = "${local.name_prefix}-ecs-task-role" }
}

resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "secrets-manager-read"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.db.arn]
    }]
  })
}

# X-Ray へのトレースデータ送信権限（xray-daemon サイドカーが使用）
# X-Ray はリソースレベル ARN 指定が非対応のため Resource = "*" が必須
resource "aws_iam_role_policy" "ecs_task_xray" {
  name = "xray-put-traces"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets",
      ]
      Resource = ["*"]
    }]
  })
}

# ── ECS クラスター ────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled" # 学習環境のためコスト抑制
  }

  tags = { Name = "${local.name_prefix}-cluster" }
}

# ── タスク定義 ────────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "512"  # 0.5 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = "${aws_ecr_repository.app.repository_url}:${var.app_image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "XRAY_ENABLED", value = "true" }
      ]

      # DB 接続情報を Secrets Manager から個別キーで注入
      secrets = [
        { name = "DB_HOST",     valueFrom = "${aws_secretsmanager_secret.db.arn}:host::" },
        { name = "DB_PORT",     valueFrom = "${aws_secretsmanager_secret.db.arn}:port::" },
        { name = "DB_NAME",     valueFrom = "${aws_secretsmanager_secret.db.arn}:dbname::" },
        { name = "DB_USER",     valueFrom = "${aws_secretsmanager_secret.db.arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db.arn}:password::" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        # curl は python:3.12-slim に存在しないため Python の urllib で代替
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }

      # xray-daemon が先に起動してからアプリを起動する
      dependsOn = [
        { containerName = "xray-daemon", condition = "START" }
      ]
    },
    {
      # AWS X-Ray デーモン：アプリコンテナからトレースデータを UDP:2000 で受け取り X-Ray へ転送
      name      = "xray-daemon"
      image     = "public.ecr.aws/xray/aws-xray-daemon:latest"
      essential = false

      portMappings = [
        {
          containerPort = 2000
          protocol      = "udp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "xray"
        }
      }
    }
  ])

  tags = { Name = "${local.name_prefix}-app" }
}

# ── ECS サービス ──────────────────────────────────────────────────────────────

resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # CodeDeploy が Blue/Green 切替を管理する（ECS ローリングアップデートを無効化）
  # 注意: deployment_controller の変更は ECS サービスの再作成が必要（一時的なダウンタイムあり）
  deployment_controller {
    type = "CODE_DEPLOY"
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 60

  lifecycle {
    # CodeDeploy がタスク定義・スケール数・ロードバランサを管理するため Terraform の上書きを防ぐ
    ignore_changes = [desired_count, task_definition, load_balancer]
  }

  depends_on = [aws_lb_listener.http]

  tags = { Name = "${local.name_prefix}-service" }
}

# ── Auto Scaling ──────────────────────────────────────────────────────────────

resource "aws_appautoscaling_target" "ecs" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = 1
  max_capacity       = 4
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${local.name_prefix}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 60.0
    scale_out_cooldown = 60  # スパイクに素早く対応
    scale_in_cooldown  = 300 # 過剰なスケールインを防ぐ
  }
}
