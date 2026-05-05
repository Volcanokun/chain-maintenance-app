# xray-daemon は public.ecr.aws から直接 pull できない（プライベートサブネット + NAT なし）
# GitHub Actions でミラーリングしてここに push する。サードパーティ映像なので MUTABLE。
resource "aws_ecr_repository" "xray_daemon" {
  name                 = "chain-maintenance-xray-daemon"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "chain-maintenance-xray-daemon" }
}

resource "aws_ecr_repository" "app" {
  name                 = "chain-maintenance-app"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true # terraform destroy 時にイメージが残っていても強制削除

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = "chain-maintenance-app" }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "最新10世代を保持し古いイメージを自動削除"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
