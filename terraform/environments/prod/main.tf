locals {
  common_tags = {
    Project     = "rentmanager"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "terraform_remote_state" "shared" {
  backend = "s3"

  config = {
    bucket = "rentmanager-terraform-state"
    key    = "environments/shared/terraform.tfstate"
    region = var.aws_region
  }
}

module "networking" {
  source = "../../modules/networking"

  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  single_nat_gateway = false
  tags               = local.common_tags
}

module "s3" {
  source = "../../modules/s3"

  environment = var.environment
  tags        = local.common_tags
}

module "eks" {
  source = "../../modules/eks"

  environment            = var.environment
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  node_security_group_id = module.networking.eks_nodes_security_group_id
  node_instance_types    = ["t3.large"]
  node_desired_size      = 2
  node_min_size          = 2
  node_max_size          = 6
  node_disk_size         = 50
  s3_bucket_arn          = module.s3.bucket_arn
  tags                   = local.common_tags
}

module "rds" {
  source = "../../modules/rds"

  environment             = var.environment
  subnet_ids              = module.networking.isolated_subnet_ids
  security_group_id       = module.networking.rds_security_group_id
  instance_class          = "db.t4g.small"
  allocated_storage       = 50
  multi_az                = true
  backup_retention_period = 7
  deletion_protection     = true
  tags                    = local.common_tags
}

module "elasticache" {
  source = "../../modules/elasticache"

  environment       = var.environment
  subnet_ids        = module.networking.isolated_subnet_ids
  security_group_id = module.networking.elasticache_security_group_id
  node_type         = "cache.t4g.small"
  num_cache_nodes   = 2
  tags              = local.common_tags
}

module "cicd" {
  source = "../../modules/cicd"

  environment              = var.environment
  github_oidc_provider_arn = data.terraform_remote_state.shared.outputs.github_oidc_provider_arn
  eks_cluster_name         = module.eks.cluster_name
  ecr_repo_arns = [
    data.terraform_remote_state.shared.outputs.ecr_backend_repo_arn,
    data.terraform_remote_state.shared.outputs.ecr_frontend_repo_arn,
  ]
  tags = local.common_tags
}

module "observability" {
  source = "../../modules/observability"

  environment                      = var.environment
  eks_cluster_name                 = module.eks.cluster_name
  rds_instance_id                  = module.rds.db_instance_id
  elasticache_replication_group_id = module.elasticache.replication_group_id
  alert_email                      = var.alert_email
  tags                             = local.common_tags
}

module "dns" {
  source = "../../modules/dns"

  environment        = var.environment
  domain_name        = var.domain_name
  subdomain          = var.subdomain
  create_hosted_zone = false
  tags               = local.common_tags
}
