variable "environment" {
  description = "Environment name"
  type        = string
}

variable "subnet_ids" {
  description = "Isolated subnet IDs"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group for ElastiCache"
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.micro"
}

variable "num_cache_nodes" {
  description = "Number of cache nodes (1 for dev, 2+ for prod replication)"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
