output "sns_topic_arn" {
  description = "SNS alerts topic ARN"
  value       = aws_sns_topic.alerts.arn
}

output "eks_log_group_name" {
  description = "EKS CloudWatch log group"
  value       = aws_cloudwatch_log_group.eks.name
}

output "rds_log_group_name" {
  description = "RDS CloudWatch log group"
  value       = aws_cloudwatch_log_group.rds.name
}
