variable "environment" {
  description = "Environment name"
  type        = string
}

variable "subnet_ids" {
  description = "Isolated subnet IDs for DB"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group for RDS"
  type        = string
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Storage in GB"
  type        = number
  default     = 20
}

variable "multi_az" {
  description = "Enable multi-AZ"
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Backup retention days"
  type        = number
  default     = 1
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "rentmanager"
}

variable "db_username" {
  description = "Master username"
  type        = string
  default     = "rentmanager"
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
