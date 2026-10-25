output "zone_id" {
  description = "Cloudflare zone ID"
  value       = data.cloudflare_zone.main.zone_id
}

output "fqdn" {
  description = "Fully qualified domain name"
  value       = local.fqdn
}
