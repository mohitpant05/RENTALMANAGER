variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain_name" {
  description = "Root domain name (e.g. mepant.com)"
  type        = string
}

variable "subdomain" {
  description = "Subdomain prefix (e.g. rm-dev)"
  type        = string
}

variable "target_address" {
  description = "IP or CNAME target for the subdomain (ALB DNS name or IP)"
  type        = string
  default     = ""
}

variable "record_type" {
  description = "DNS record type (A for IP, CNAME for ALB DNS name)"
  type        = string
  default     = "CNAME"
}

variable "proxied" {
  description = "Enable Cloudflare proxy (orange cloud)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags (not used by Cloudflare but kept for interface consistency)"
  type        = map(string)
  default     = {}
}
