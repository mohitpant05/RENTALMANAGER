terraform {
  backend "s3" {
    bucket         = "rentmanager-terraform-state"
    key            = "environments/shared/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "rentmanager-terraform-locks"
    encrypt        = true
  }
}
