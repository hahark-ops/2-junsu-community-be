output "vpc_id" {
  value = aws_vpc.main.id
}

output "alb_dns_name" {
  value = try(aws_lb.app[0].dns_name, null)
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
  value = var.enable_rds ? aws_db_instance.main[0].address : null
}

output "rds_port" {
  value = var.enable_rds ? aws_db_instance.main[0].port : null
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
  value = try(aws_s3_bucket.cloudtrail[0].id, null)
}

output "efs_id" {
  value = try(aws_efs_file_system.shared[0].id, null)
}

output "athena_workgroup_name" {
  value = aws_athena_workgroup.analytics.name
}

output "athena_results_bucket_name" {
  value = aws_s3_bucket.athena_results.id
}

output "ecs_cluster_name" {
  value = var.enable_ecs ? aws_ecs_cluster.main[0].name : null
}

output "ecs_service_name" {
  value = var.enable_ecs ? aws_ecs_service.be[0].name : null
}

output "ecs_task_family" {
  value = var.enable_ecs ? aws_ecs_task_definition.be[0].family : null
}

output "ecs_target_group_arn" {
  value = var.enable_ecs ? aws_lb_target_group.ecs_be[0].arn : null
}
