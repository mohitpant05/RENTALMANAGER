output "vpc_id" {
  value = module.networking.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  value     = module.rds.db_endpoint
  sensitive = true
}

output "redis_endpoint" {
  value     = module.elasticache.redis_endpoint
  sensitive = true
}

output "s3_bucket_name" {
  value = module.s3.bucket_name
}

output "ecr_backend_url" {
  value = data.terraform_remote_state.shared.outputs.ecr_backend_repo_url
}

output "ecr_frontend_url" {
  value = data.terraform_remote_state.shared.outputs.ecr_frontend_repo_url
}

output "github_deploy_role_arn" {
  value = module.cicd.github_deploy_role_arn
}

output "app_url" {
  value = module.dns.fqdn
}
