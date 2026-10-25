terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }
}

locals {
  fqdn = "${var.subdomain}.${var.domain_name}"
}

data "cloudflare_zone" "main" {
  filter = {
    name = var.domain_name
  }
}

resource "cloudflare_dns_record" "app" {
  count   = var.target_address != "" ? 1 : 0
  zone_id = data.cloudflare_zone.main.zone_id
  name    = var.subdomain
  content = var.target_address
  type    = var.record_type
  proxied = var.proxied
  ttl     = var.proxied ? 1 : 300
}

resource "cloudflare_dns_record" "app_wildcard" {
  count   = var.target_address != "" ? 1 : 0
  zone_id = data.cloudflare_zone.main.zone_id
  name    = "*.${var.subdomain}"
  content = var.target_address
  type    = var.record_type
  proxied = var.proxied
  ttl     = var.proxied ? 1 : 300
}
