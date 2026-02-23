output "vpc_id" {
  value = aws_vpc.main.id
}

output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "fe_public_ip" {
  value = var.assign_eip ? aws_eip.fe[0].public_ip : aws_instance.fe.public_ip
}

output "be_public_ip" {
  value = var.assign_eip ? aws_eip.be[0].public_ip : aws_instance.be.public_ip
}

output "be_private_ip" {
  value = aws_instance.be.private_ip
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "upload_bucket_name" {
  value = aws_s3_bucket.uploads.id
}

output "upload_api_base_url" {
  value = aws_apigatewayv2_api.upload_api.api_endpoint
}

output "upload_api_route_url" {
  value = "${aws_apigatewayv2_api.upload_api.api_endpoint}/v1/files/upload"
}

output "analytics_api_route_url" {
  value = "${aws_apigatewayv2_api.upload_api.api_endpoint}/v1/analytics/health"
}

output "cloudtrail_bucket_name" {
  value = aws_s3_bucket.cloudtrail.id
}

output "efs_id" {
  value = aws_efs_file_system.shared.id
}

output "athena_workgroup_name" {
  value = aws_athena_workgroup.analytics.name
}

output "athena_results_bucket_name" {
  value = aws_s3_bucket.athena_results.id
}
