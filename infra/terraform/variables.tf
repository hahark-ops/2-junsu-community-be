variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "프로젝트 이름 prefix"
  type        = string
  default     = "community"
}

variable "environment" {
  description = "환경 이름 (dev, prod 등)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.20.0.0/16"
}

variable "admin_cidr" {
  description = "SSH 허용 CIDR (예: 1.2.3.4/32)"
  type        = string

  validation {
    condition     = var.admin_cidr != "0.0.0.0/0"
    error_message = "admin_cidr에 0.0.0.0/0을 사용할 수 없습니다. 현재 공인 IP/32만 허용하세요."
  }
}

variable "key_pair_name" {
  description = "EC2 접속용 Key Pair 이름"
  type        = string
}

variable "ami_id" {
  description = "선택: 고정 AMI ID (빈값이면 최신 Amazon Linux 2023 사용)"
  type        = string
  default     = ""
}

variable "fe_instance_type" {
  description = "FE EC2 인스턴스 타입"
  type        = string
  default     = "t3.small"
}

variable "be_instance_type" {
  description = "BE EC2 인스턴스 타입"
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "RDS 인스턴스 클래스"
  type        = string
  default     = "db.t3.micro"
}

variable "enable_rds" {
  description = "RDS 리소스 생성 여부"
  type        = bool
  default     = false
}

variable "db_host_override" {
  description = "RDS 비사용 시 DB 호스트(예: EC2 내부 MySQL IP)"
  type        = string
  default     = ""
}

variable "db_name" {
  description = "RDS DB 이름"
  type        = string
  default     = "community_db"
}

variable "db_username" {
  description = "RDS 사용자명"
  type        = string
  default     = "community_user"
}

variable "db_password" {
  description = "RDS 비밀번호"
  type        = string
  sensitive   = true
}

variable "db_allocated_storage" {
  description = "RDS 기본 저장공간(GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS 자동 확장 최대 저장공간(GB)"
  type        = number
  default     = 100
}

variable "assign_eip" {
  description = "FE/BE 인스턴스에 Elastic IP 연결 여부"
  type        = bool
  default     = true
}

variable "minimal_cost_mode" {
  description = "기본 apply에서 NAT/ALB/EFS/CloudTrail 같은 상시 과금 리소스를 비활성화할지 여부"
  type        = bool
  default     = true
}

variable "enable_nat_gateway" {
  description = "Private subnet outbound용 NAT Gateway 생성 여부"
  type        = bool
  default     = false
}

variable "enable_alb" {
  description = "ALB 생성 여부"
  type        = bool
  default     = false
}

variable "enable_efs" {
  description = "EFS 생성 여부"
  type        = bool
  default     = false
}

variable "enable_cloudtrail" {
  description = "CloudTrail 생성 여부"
  type        = bool
  default     = false
}

variable "upload_bucket_name" {
  description = "선택: 업로드용 S3 버킷명 (비우면 자동 생성)"
  type        = string
  default     = ""
}

variable "cloudtrail_bucket_name" {
  description = "선택: CloudTrail 로그 버킷명 (비우면 자동 생성)"
  type        = string
  default     = ""
}

variable "athena_results_bucket_name" {
  description = "선택: Athena 쿼리 결과 버킷명 (비우면 자동 생성)"
  type        = string
  default     = ""
}

variable "upload_allowed_origin" {
  description = "업로드 경로(S3/Lambda) CORS 허용 Origin (단일 Origin)"
  type        = string
  default     = "http://localhost:3000"

  validation {
    condition     = trimspace(var.upload_allowed_origin) != "*" && can(regex("^https?://", trimspace(var.upload_allowed_origin)))
    error_message = "upload_allowed_origin은 '*'를 사용할 수 없으며 http(s) 단일 Origin 형식이어야 합니다. 예: http://localhost:3000"
  }
}

variable "fe_repo_url" {
  description = "선택: FE Git 저장소 URL (비우면 user_data에서 clone 생략)"
  type        = string
  default     = ""
}

variable "fe_repo_branch" {
  description = "FE Git branch"
  type        = string
  default     = "main"
}

variable "be_repo_url" {
  description = "선택: BE Git 저장소 URL (비우면 user_data에서 clone 생략)"
  type        = string
  default     = ""
}

variable "be_repo_branch" {
  description = "BE Git branch"
  type        = string
  default     = "main"
}

variable "enable_alb_be_api_rule" {
  description = "ALB에서 /v1, /docs를 BE 타겟그룹으로 직접 우회할지 여부"
  type        = bool
  default     = false
}

variable "enable_ecs" {
  description = "ECS Fargate 리소스 생성 여부"
  type        = bool
  default     = false
}

variable "ecs_cpu" {
  description = "ECS Task CPU"
  type        = number
  default     = 512
}

variable "ecs_memory" {
  description = "ECS Task Memory(MB)"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "ECS Service desired count"
  type        = number
  default     = 1
}

variable "ecs_container_port" {
  description = "ECS 컨테이너 포트"
  type        = number
  default     = 8000
}

variable "ecs_assign_public_ip" {
  description = "ECS task에 public IP 할당 여부"
  type        = bool
  default     = false
}

variable "ecs_health_check_path" {
  description = "ECS target group health check path"
  type        = string
  default     = "/healthz/ready"
}

variable "ecs_path_patterns" {
  description = "ALB listener rule path patterns for ECS service"
  type        = list(string)
  default     = ["/ecs/*"]
}

variable "ecs_be_bootstrap_image" {
  description = "ECS 초기 task definition bootstrap image"
  type        = string
  default     = "public.ecr.aws/docker/library/python:3.11-slim"
}
