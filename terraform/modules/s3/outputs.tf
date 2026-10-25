output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.uploads.arn
}

output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.uploads.bucket
}

output "bucket_regional_domain_name" {
  description = "S3 bucket regional domain"
  value       = aws_s3_bucket.uploads.bucket_regional_domain_name
}
