variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "github_org" {
  description = "GitHub org or username"
  type        = string
  default     = "mohitpant05"
}

variable "github_repo" {
  description = "GitHub repo name"
  type        = string
  default     = "RM"
}
