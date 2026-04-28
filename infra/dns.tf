# Cloudflare Zone参照
data "cloudflare_zone" "main" {
  name = "volcanokun.dev"
}

# ACM証明書
resource "aws_acm_certificate" "main" {
  domain_name       = "chain-app.volcanokun.dev"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# ACM DNS検証レコード（Cloudflareに作成）
resource "cloudflare_record" "acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }

  zone_id = data.cloudflare_zone.main.id
  name    = each.value.name
  content = each.value.value
  type    = each.value.type
  ttl     = 60
  proxied = false
}

# ACM証明書の検証完了を待つ
resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in cloudflare_record.acm_validation : record.hostname]
}

# CNAMEレコード（chain-app.volcanokun.dev → ALB）
resource "cloudflare_record" "chain_app" {
  zone_id = data.cloudflare_zone.main.id
  name    = "chain-app"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  ttl     = 1
  proxied = false
}

# ALB HTTPSリスナー（443）
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
