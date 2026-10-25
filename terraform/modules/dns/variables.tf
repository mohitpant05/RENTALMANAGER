variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain_name" {
  description = "Root domain name (e.g. yourdomain.com)"
  type        = string
}

variable "subdomain" {
  description = "Subdomain prefix (e.g. rm-dev)"
  type        = string
}

variable "alb_dns_name" {
  description = "ALB DNS name to point the subdomain at"
  type        = string
  default     = ""
}

variable "alb_zone_id" {
  description = "ALB hosted zone ID for alias record"
  type        = string
  default     = ""
}

variable "create_hosted_zone" {
  description = "Create a new hosted zone (false to use existing)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
