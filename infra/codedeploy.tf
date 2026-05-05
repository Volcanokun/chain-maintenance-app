# ── HTTPS リスナー参照（dns.tf が作成するリスナーを port で自動検索）─────────
# dns.tf は git 管理外のためリソース名を直接参照できない。
# data source で ALB + port 443 を条件に引くことで tfvars への手動記載を不要にする。
data "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443

  # ALB が存在してから読む（初回 apply 時に ALB 作成 → リスナー作成 → data source 参照の順を保証）
  depends_on = [aws_lb.main]
}

# ── CodeDeploy IAM Role ───────────────────────────────────────────────────────

data "aws_iam_policy_document" "codedeploy_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codedeploy.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codedeploy" {
  name               = "${local.name_prefix}-codedeploy-role"
  assume_role_policy = data.aws_iam_policy_document.codedeploy_assume.json

  tags = { Name = "${local.name_prefix}-codedeploy-role" }
}

# ECS Blue/Green デプロイに必要な権限（ECS 更新・ALB TG 操作・CloudWatch Events）
resource "aws_iam_role_policy_attachment" "codedeploy_ecs" {
  role       = aws_iam_role.codedeploy.name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}

# ── CodeDeploy Application ────────────────────────────────────────────────────

resource "aws_codedeploy_app" "ecs" {
  name             = "${local.name_prefix}-deploy-app"
  compute_platform = "ECS"

  tags = { Name = "${local.name_prefix}-deploy-app" }
}

# ── CodeDeploy Deployment Group ───────────────────────────────────────────────

resource "aws_codedeploy_deployment_group" "ecs" {
  app_name              = aws_codedeploy_app.ecs.name
  deployment_group_name = "${local.name_prefix}-deploy-group"
  service_role_arn      = aws_iam_role.codedeploy.arn

  # ECSAllAtOnce: 全トラフィックを一括切替（学習環境向け、Canary/Linear より高速）
  deployment_config_name = "CodeDeployDefault.ECSAllAtOnce"

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.app.name
  }

  deployment_style {
    deployment_option = "WITH_TRAFFIC_CONTROL"
    deployment_type   = "BLUE_GREEN"
  }

  load_balancer_info {
    target_group_pair_info {
      # 本番リスナー（HTTPS 443）: CodeDeploy がトラフィックを Blue↔Green で切替
      prod_traffic_route {
        listener_arns = [data.aws_lb_listener.https.arn]
      }
      # テストリスナー（HTTP 8080）: 切替前に Green タスクを手動・自動検証する口
      test_traffic_route {
        listener_arns = [aws_lb_listener.test.arn]
      }
      # Blue TG（既存）
      target_group {
        name = aws_lb_target_group.app.name
      }
      # Green TG（新バージョンのタスクをここに立ち上げてから切替）
      target_group {
        name = aws_lb_target_group.app_green.name
      }
    }
  }

  blue_green_deployment_config {
    # タイムアウトを待たず即時切替（学習環境では手動承認ステップを省略）
    deployment_ready_option {
      action_on_timeout = "CONTINUE_DEPLOYMENT"
    }
    # 切替成功後 5 分待って Blue タスクを終了（問題発覚時のロールバック猶予）
    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }

  tags = { Name = "${local.name_prefix}-deploy-group" }
}
