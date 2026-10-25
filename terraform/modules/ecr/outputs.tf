output "repository_urls" {
  description = "Map of repo name to URL"
  value       = { for k, v in aws_ecr_repository.repos : k => v.repository_url }
}

output "backend_repo_url" {
  description = "Backend ECR repo URL"
  value       = aws_ecr_repository.repos["rentmanager-backend"].repository_url
}

output "frontend_repo_url" {
  description = "Frontend ECR repo URL"
  value       = aws_ecr_repository.repos["rentmanager-frontend"].repository_url
}

output "backend_repo_arn" {
  description = "Backend ECR repo ARN"
  value       = aws_ecr_repository.repos["rentmanager-backend"].arn
}

output "frontend_repo_arn" {
  description = "Frontend ECR repo ARN"
  value       = aws_ecr_repository.repos["rentmanager-frontend"].arn
}
