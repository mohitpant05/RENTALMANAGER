variable "state_bucket_name" {
  description = "S3 bucket for Terraform state"
  type        = string
  default     = "rentmanager-terraform-state"
}

variable "lock_table_name" {
  description = "DynamoDB table for state locking"
  type        = string
  default     = "rentmanager-terraform-locks"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}
