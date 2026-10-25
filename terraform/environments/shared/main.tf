locals {
  common_tags = {
    Project   = "rentmanager"
    ManagedBy = "terraform"
  }
}

module "ecr" {
  source = "../../modules/ecr"

  tags = local.common_tags
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"]

  tags = local.common_tags
}
