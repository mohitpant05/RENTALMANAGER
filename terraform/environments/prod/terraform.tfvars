aws_region         = "ap-south-1"
environment        = "prod"
vpc_cidr           = "10.1.0.0/16"
availability_zones = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
alert_email        = ""
domain_name        = "mepant.com"
subdomain          = "rm-prod"

# cloudflare_api_token — pass via env var:
# export TF_VAR_cloudflare_api_token="your-token-here"
