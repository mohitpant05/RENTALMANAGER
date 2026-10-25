locals {
  fqdn = "${var.subdomain}.${var.domain_name}"
}

data "aws_route53_zone" "existing" {
  count = var.create_hosted_zone ? 0 : 1
  name  = var.domain_name
}

resource "aws_route53_zone" "new" {
  count = var.create_hosted_zone ? 1 : 0
  name  = var.domain_name

  tags = merge(var.tags, {
    Name = var.domain_name
  })
}

locals {
  zone_id = var.create_hosted_zone ? aws_route53_zone.new[0].zone_id : data.aws_route53_zone.existing[0].zone_id
}

resource "aws_route53_record" "app" {
  count   = var.alb_dns_name != "" ? 1 : 0
  zone_id = local.zone_id
  name    = local.fqdn
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app_wildcard" {
  count   = var.alb_dns_name != "" ? 1 : 0
  zone_id = local.zone_id
  name    = "*.${local.fqdn}"
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
