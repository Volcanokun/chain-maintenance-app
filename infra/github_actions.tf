variable "github_org" {
  description = "GitHub Organization またはユーザー名（例: your-org）"
  type        = string
}

variable "github_repo" {
  description = "GitHub リポジトリ名（例: chain-maintenance-app）"
  type        = string
}

# ── 現在の AWS アカウント情報 ─────────────────────────────────────────────────

data "aws_caller_identity" "current" {}

# ── GitHub Actions OIDC プロバイダー ─────────────────────────────────────────
# AWS は 2023/10 以降 GitHub の OIDC サムプリントを自動管理するため
# thumbprint_list の値は検証されないが、Terraform の必須フィールドとして指定する

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = { Name = "${local.name_prefix}-github-actions-oidc" }
}

# ── GitHub Actions IAM ロール ─────────────────────────────────────────────────

resource "aws_iam_role" "github_actions" {
  name = "${local.name_prefix}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          # main ブランチへの push のみに制限
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
          }
        }
      }
    ]
  })

  tags = { Name = "${local.name_prefix}-github-actions-role" }
}

# ── GitHub Actions IAM ポリシー ───────────────────────────────────────────────

resource "aws_iam_role_policy" "github_actions" {
  name = "github-actions-deploy-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [

      # ECR 認証トークン取得（リソース指定不可のため * 必須）
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },

      # ECR イメージプッシュ（リポジトリ限定）
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
        ]
        Resource = aws_ecr_repository.app.arn
      },

      # ECS サービス情報取得・タスク定義登録・マイグレーションタスク実行
      {
        Sid    = "ECSDescribe"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
        ]
        Resource = "*"
      },
      {
        # 新イメージ（sha タグ）を使った新リビジョン登録（RegisterTaskDefinition は Resource: * 必須）
        Sid      = "ECSRegisterTaskDef"
        Effect   = "Allow"
        Action   = ["ecs:RegisterTaskDefinition"]
        Resource = "*"
      },
      {
        Sid    = "ECSRunMigration"
        Effect = "Allow"
        Action = ["ecs:RunTask"]
        # タスク定義はリビジョンが変わるため family レベルで許可
        Resource = "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.name_prefix}-app:*"
      },

      # ECS RunTask 時に実行ロール・タスクロールを渡すために必要
      {
        Sid    = "PassRoleToECS"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_task.arn,
        ]
      },

      # マイグレーションタスクのログ確認
      {
        Sid      = "CloudWatchLogs"
        Effect   = "Allow"
        Action   = ["logs:GetLogEvents", "logs:DescribeLogStreams"]
        Resource = "${aws_cloudwatch_log_group.ecs.arn}:*"
      },

      # CodeDeploy: デプロイ作成・リビジョン登録（アプリ・デプロイグループ限定）
      {
        Sid    = "CodeDeployApp"
        Effect = "Allow"
        Action = [
          "codedeploy:CreateDeployment",
          "codedeploy:RegisterApplicationRevision",
          "codedeploy:GetApplicationRevision",
        ]
        Resource = [
          aws_codedeploy_app.ecs.arn,
          aws_codedeploy_deployment_group.ecs.arn,
        ]
      },

      # CodeDeploy: デプロイ状態確認（デプロイ ID は動的のため account スコープで制限）
      {
        Sid    = "CodeDeployStatus"
        Effect = "Allow"
        Action = [
          "codedeploy:GetDeployment",
          "codedeploy:GetDeploymentConfig",
        ]
        Resource = [
          "arn:aws:codedeploy:${var.aws_region}:${data.aws_caller_identity.current.account_id}:deployment:*",
          "arn:aws:codedeploy:${var.aws_region}:${data.aws_caller_identity.current.account_id}:deploymentconfig:*",
        ]
      },
    ]
  })
}
