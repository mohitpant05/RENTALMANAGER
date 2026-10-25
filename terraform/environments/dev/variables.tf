variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "availability_zones" {
  description = "AZs to use"
  type        = list(string)
}

variable "alert_email" {
  description = "Email for CloudWatch alarm notifications"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Root domain name for Route53"
  type        = string
  default     = ""
}

variable "subdomain" {
  description = "Subdomain prefix (e.g. rm-dev)"
  type        = string
  default     = "rm-dev"
}
