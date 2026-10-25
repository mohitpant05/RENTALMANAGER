variable "environment" {
  description = "Environment name"
  type        = string
}

variable "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider (created in shared environment)"
  type        = string
}

variable "eks_cluster_name" {
  description = "EKS cluster name for deploy permissions"
  type        = string
}

variable "ecr_repo_arns" {
  description = "List of ECR repo ARNs"
  type        = list(string)
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
