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
  description = "S3 CORS 허용 Origin"
  type        = string
  default     = "*"
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
