output "zone_id" {
  description = "Route53 hosted zone ID"
  value       = local.zone_id
}

output "fqdn" {
  description = "Fully qualified domain name"
  value       = local.fqdn
}

output "nameservers" {
  description = "NS records (only for newly created zones)"
  value       = var.create_hosted_zone ? aws_route53_zone.new[0].name_servers : []
}
