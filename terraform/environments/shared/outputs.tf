output "ecr_backend_repo_url" {
  description = "Backend ECR repo URL"
  value       = module.ecr.backend_repo_url
}

output "ecr_frontend_repo_url" {
  description = "Frontend ECR repo URL"
  value       = module.ecr.frontend_repo_url
}

output "ecr_backend_repo_arn" {
  description = "Backend ECR repo ARN"
  value       = module.ecr.backend_repo_arn
}

output "ecr_frontend_repo_arn" {
  description = "Frontend ECR repo ARN"
  value       = module.ecr.frontend_repo_arn
}

output "github_oidc_provider_arn" {
  description = "GitHub OIDC provider ARN"
  value       = aws_iam_openid_connect_provider.github.arn
}
