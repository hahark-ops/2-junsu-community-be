data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  name_prefix        = lower(replace("${var.project_name}-${var.environment}", "_", "-"))
  ecs_task_family    = "${local.name_prefix}-be-task"
  ecs_container_name = "${local.name_prefix}-be-container"

  ami_id = var.ami_id != "" ? var.ami_id : data.aws_ami.al2023.id

  upload_bucket_name         = var.upload_bucket_name != "" ? var.upload_bucket_name : "${local.name_prefix}-uploads-${random_id.suffix.hex}"
  trail_bucket_name          = var.cloudtrail_bucket_name != "" ? var.cloudtrail_bucket_name : "${local.name_prefix}-trail-${random_id.suffix.hex}"
  athena_results_bucket_name = var.athena_results_bucket_name != "" ? var.athena_results_bucket_name : "${local.name_prefix}-athena-${random_id.suffix.hex}"

  rds_endpoint = try(aws_db_instance.main[0].address, null)
  rds_port     = try(tostring(aws_db_instance.main[0].port), "3306")

  db_host = var.enable_rds ? local.rds_endpoint : (
    trimspace(var.db_host_override) != "" ? trimspace(var.db_host_override) : "db"
  )
  db_port = var.enable_rds ? local.rds_port : "3306"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------
# VPC / Subnets / Routing
# -----------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-igw"
  })
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-${count.index + 1}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index + 8)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-${count.index + 1}"
    Tier = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = 2

  route_table_id = aws_route_table.public.id
  subnet_id      = aws_subnet.public[count.index].id
}

# Lambda in private subnets needs outbound internet to call public API Gateway endpoints.
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-eip"
  })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat"
  })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-rt"
  })
}

resource "aws_route_table_association" "private" {
  count = 2

  route_table_id = aws_route_table.private.id
  subnet_id      = aws_subnet.private[count.index].id
}

# -----------------------------
# Security Groups
# -----------------------------
resource "aws_security_group" "alb" {
  name_prefix = "${local.name_prefix}-alb-"
  description = "ALB SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-alb-sg" })
}

resource "aws_security_group" "fe" {
  name_prefix = "${local.name_prefix}-fe-"
  description = "FE EC2 SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "FE app from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description = "SSH from admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-fe-sg" })
}

resource "aws_security_group" "be" {
  name_prefix = "${local.name_prefix}-be-"
  description = "BE EC2 SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "BE api from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "BE api from FE server"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.fe.id]
  }

  ingress {
    description = "SSH from admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-be-sg" })
}

resource "aws_security_group" "ecs_tasks" {
  count = var.enable_ecs ? 1 : 0

  name_prefix = "${local.name_prefix}-ecs-"
  description = "ECS task SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "ECS api from ALB"
    from_port       = var.ecs_container_port
    to_port         = var.ecs_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-ecs-sg" })
}

resource "aws_security_group" "rds" {
  count = var.enable_rds ? 1 : 0

  name_prefix = "${local.name_prefix}-rds-"
  description = "RDS SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MySQL from BE"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.be.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-rds-sg" })
}

resource "aws_security_group_rule" "rds_from_ecs" {
  count = var.enable_rds && var.enable_ecs ? 1 : 0

  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds[0].id
  source_security_group_id = aws_security_group.ecs_tasks[0].id
  description              = "MySQL from ECS tasks"
}

resource "aws_security_group" "efs" {
  name_prefix = "${local.name_prefix}-efs-"
  description = "EFS SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from BE"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.be.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-efs-sg" })
}

# -----------------------------
# IAM (EC2 / Lambda)
# -----------------------------
resource "aws_iam_role" "ec2" {
  name_prefix = "${local.name_prefix}-ec2-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ec2_ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ec2_cwagent" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "ec2_ecr_readonly" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2" {
  name_prefix = "${local.name_prefix}-ec2-profile-"
  role        = aws_iam_role.ec2.name
}

resource "aws_iam_role" "lambda_upload" {
  name_prefix = "${local.name_prefix}-lambda-upload-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_upload.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_upload_s3" {
  name_prefix = "${local.name_prefix}-lambda-upload-s3-"
  role        = aws_iam_role.lambda_upload.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ],
        Resource = "${aws_s3_bucket.uploads.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role" "lambda_analytics" {
  name_prefix = "${local.name_prefix}-lambda-analytics-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_analytics_basic_logs" {
  role       = aws_iam_role.lambda_analytics.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_analytics_athena" {
  name_prefix = "${local.name_prefix}-lambda-analytics-athena-"
  role        = aws_iam_role.lambda_analytics.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        Resource = [
          aws_s3_bucket.athena_results.arn
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource = [
          "${aws_s3_bucket.athena_results.arn}/*"
        ]
      }
    ]
  })
}

# -----------------------------
# ECS Fargate (optional)
# -----------------------------
resource "aws_ecs_cluster" "main" {
  count = var.enable_ecs ? 1 : 0

  name = "${local.name_prefix}-ecs-cluster"

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "ecs_be" {
  count = var.enable_ecs ? 1 : 0

  name              = "/ecs/${local.name_prefix}-be"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_iam_role" "ecs_task_execution" {
  count = var.enable_ecs ? 1 : 0

  name_prefix = "${local.name_prefix}-ecs-exec-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_default" {
  count = var.enable_ecs ? 1 : 0

  role       = aws_iam_role.ecs_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  count = var.enable_ecs ? 1 : 0

  name_prefix = "${local.name_prefix}-ecs-task-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "be" {
  count = var.enable_ecs ? 1 : 0

  family                   = local.ecs_task_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.ecs_cpu)
  memory                   = tostring(var.ecs_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution[0].arn
  task_role_arn            = aws_iam_role.ecs_task[0].arn

  container_definitions = jsonencode([
    {
      name      = local.ecs_container_name
      image     = var.ecs_be_bootstrap_image
      essential = true
      command   = ["python", "-m", "http.server", tostring(var.ecs_container_port)]
      portMappings = [
        {
          containerPort = var.ecs_container_port
          hostPort      = var.ecs_container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "DB_HOST", value = local.db_host },
        { name = "DB_PORT", value = local.db_port },
        { name = "DB_USER", value = var.db_username },
        { name = "DB_PASSWORD", value = var.db_password },
        { name = "DB_NAME", value = var.db_name },
        { name = "CORS_ALLOW_ORIGINS", value = var.upload_allowed_origin },
        { name = "COOKIE_SECURE", value = "false" },
        { name = "COOKIE_SAMESITE", value = "lax" },
        { name = "COOKIE_MAX_AGE", value = "604800" },
        { name = "UPLOAD_PROVIDER", value = "lambda" },
        { name = "UPLOAD_LAMBDA_API_URL", value = "${aws_apigatewayv2_api.upload_api.api_endpoint}/v1/files/upload-url" },
        { name = "MAX_UPLOAD_SIZE_BYTES", value = "26214400" },
        { name = "MAX_PROFILE_UPLOAD_SIZE_BYTES", value = "26214400" },
        { name = "MAX_POST_UPLOAD_SIZE_BYTES", value = "31457280" },
        { name = "BCRYPT_ROUNDS", value = "12" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_be[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "be"
        }
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_ecs_service" "be" {
  count = var.enable_ecs ? 1 : 0

  name            = "${local.name_prefix}-be-service"
  cluster         = aws_ecs_cluster.main[0].id
  task_definition = aws_ecs_task_definition.be[0].arn
  launch_type     = "FARGATE"
  desired_count   = var.ecs_desired_count

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks[0].id]
    assign_public_ip = var.ecs_assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ecs_be[0].arn
    container_name   = local.ecs_container_name
    container_port   = var.ecs_container_port
  }

  depends_on = [
    aws_lb_listener_rule.ecs_api,
    aws_iam_role_policy_attachment.ecs_task_execution_default
  ]

  tags = local.common_tags
}

# -----------------------------
# EC2 (FE / BE) + Elastic IP
# -----------------------------
resource "aws_instance" "be" {
  ami                         = local.ami_id
  instance_type               = var.be_instance_type
  subnet_id                   = aws_subnet.public[1].id
  key_name                    = var.key_pair_name
  vpc_security_group_ids      = [aws_security_group.be.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  associate_public_ip_address = true

  user_data = templatefile("${path.module}/templates/user_data_be.sh.tftpl", {
    be_repo_url    = var.be_repo_url
    be_repo_branch = var.be_repo_branch
    aws_region     = var.aws_region
    efs_id         = aws_efs_file_system.shared.id
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-be-ec2"
    Role = "be"
  })
}

resource "aws_instance" "fe" {
  ami                         = local.ami_id
  instance_type               = var.fe_instance_type
  subnet_id                   = aws_subnet.public[0].id
  key_name                    = var.key_pair_name
  vpc_security_group_ids      = [aws_security_group.fe.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  associate_public_ip_address = true

  user_data = templatefile("${path.module}/templates/user_data_fe.sh.tftpl", {
    fe_repo_url    = var.fe_repo_url
    fe_repo_branch = var.fe_repo_branch
    be_private_ip  = aws_instance.be.private_ip
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-fe-ec2"
    Role = "fe"
  })
}

resource "aws_eip" "fe" {
  count  = var.assign_eip ? 1 : 0
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-fe-eip"
  })
}

resource "aws_eip_association" "fe" {
  count         = var.assign_eip ? 1 : 0
  instance_id   = aws_instance.fe.id
  allocation_id = aws_eip.fe[0].id
}

resource "aws_eip" "be" {
  count  = var.assign_eip ? 1 : 0
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-be-eip"
  })
}

resource "aws_eip_association" "be" {
  count         = var.assign_eip ? 1 : 0
  instance_id   = aws_instance.be.id
  allocation_id = aws_eip.be[0].id
}

# -----------------------------
# ELB (ALB)
# -----------------------------
resource "aws_lb" "app" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb"
  })
}

resource "aws_lb_target_group" "fe" {
  name        = "${local.name_prefix}-fe-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    enabled             = true
    path                = "/login.html"
    protocol            = "HTTP"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = local.common_tags
}

resource "aws_lb_target_group" "be" {
  name        = "${local.name_prefix}-be-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    enabled             = true
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = local.common_tags
}

resource "aws_lb_target_group" "ecs_be" {
  count = var.enable_ecs ? 1 : 0

  name        = "${local.name_prefix}-ecs-tg"
  port        = var.ecs_container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = var.ecs_health_check_path
    protocol            = "HTTP"
    matcher             = "200-399"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = local.common_tags
}

resource "aws_lb_target_group_attachment" "fe" {
  target_group_arn = aws_lb_target_group.fe.arn
  target_id        = aws_instance.fe.id
  port             = 3000
}

resource "aws_lb_target_group_attachment" "be" {
  target_group_arn = aws_lb_target_group.be.arn
  target_id        = aws_instance.be.id
  port             = 8000
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.fe.arn
  }
}

resource "aws_lb_listener_rule" "be_api" {
  count = var.enable_alb_be_api_rule ? 1 : 0

  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.be.arn
  }

  condition {
    path_pattern {
      values = ["/v1/*", "/docs*", "/openapi.json"]
    }
  }
}

resource "aws_lb_listener_rule" "ecs_api" {
  count = var.enable_ecs ? 1 : 0

  listener_arn = aws_lb_listener.http.arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecs_be[0].arn
  }

  condition {
    path_pattern {
      values = var.ecs_path_patterns
    }
  }
}

# -----------------------------
# RDS
# -----------------------------
resource "aws_db_subnet_group" "main" {
  count = var.enable_rds ? 1 : 0

  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

resource "aws_db_instance" "main" {
  count = var.enable_rds ? 1 : 0

  identifier                 = "${local.name_prefix}-mysql"
  engine                     = "mysql"
  engine_version             = "8.0"
  instance_class             = var.db_instance_class
  allocated_storage          = var.db_allocated_storage
  max_allocated_storage      = var.db_max_allocated_storage
  db_name                    = var.db_name
  username                   = var.db_username
  password                   = var.db_password
  db_subnet_group_name       = aws_db_subnet_group.main[0].name
  vpc_security_group_ids     = [aws_security_group.rds[0].id]
  publicly_accessible        = false
  backup_retention_period    = 1
  skip_final_snapshot        = true
  deletion_protection        = false
  storage_encrypted          = true
  auto_minor_version_upgrade = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds"
  })
}

# -----------------------------
# EFS
# -----------------------------
resource "aws_efs_file_system" "shared" {
  creation_token = "${local.name_prefix}-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-efs"
  })
}

resource "aws_efs_mount_target" "private" {
  count = 2

  file_system_id  = aws_efs_file_system.shared.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# -----------------------------
# S3 (uploads)
# -----------------------------
resource "aws_s3_bucket" "uploads" {
  bucket = local.upload_bucket_name

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-uploads"
  })
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_s3_bucket" "athena_results" {
  bucket = local.athena_results_bucket_name

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-athena-results"
  })
}

resource "aws_s3_bucket_versioning" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "expire-athena-query-results"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "HEAD"]
    allowed_origins = [var.upload_allowed_origin]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

data "aws_iam_policy_document" "uploads_public_read" {
  statement {
    sid     = "PublicReadUploadsPrefix"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.uploads.arn}/uploads/*"
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "uploads_public_read" {
  bucket = aws_s3_bucket.uploads.id
  policy = data.aws_iam_policy_document.uploads_public_read.json
}

# -----------------------------
# Lambda + API Gateway (업로드 전용)
# -----------------------------
resource "aws_cloudwatch_log_group" "lambda_upload" {
  name              = "/aws/lambda/${local.name_prefix}-upload-handler"
  retention_in_days = 14

  tags = local.common_tags
}

data "archive_file" "upload_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/build/upload_lambda.zip"
}

resource "aws_lambda_function" "upload_handler" {
  function_name = "${local.name_prefix}-upload-handler"
  role          = aws_iam_role.lambda_upload.arn
  filename      = data.archive_file.upload_lambda.output_path
  runtime       = "nodejs18.x"
  handler       = "index.handler"
  timeout       = 15
  memory_size   = 256

  source_code_hash = data.archive_file.upload_lambda.output_base64sha256

  environment {
    variables = {
      UPLOAD_BUCKET = aws_s3_bucket.uploads.id
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_upload]

  tags = local.common_tags
}

resource "aws_athena_workgroup" "analytics" {
  name  = "${local.name_prefix}-analytics-wg"
  state = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.id}/results/"
    }
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "lambda_analytics" {
  name              = "/aws/lambda/${local.name_prefix}-analytics-handler"
  retention_in_days = 14

  tags = local.common_tags
}

data "archive_file" "analytics_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_analytics"
  output_path = "${path.module}/build/analytics_lambda.zip"
}

resource "aws_lambda_function" "analytics_handler" {
  function_name = "${local.name_prefix}-analytics-handler"
  role          = aws_iam_role.lambda_analytics.arn
  filename      = data.archive_file.analytics_lambda.output_path
  runtime       = "nodejs18.x"
  handler       = "index.handler"
  timeout       = 20
  memory_size   = 256

  source_code_hash = data.archive_file.analytics_lambda.output_base64sha256

  environment {
    variables = {
      ATHENA_WORKGROUP = aws_athena_workgroup.analytics.name
      ATHENA_OUTPUT_S3 = "s3://${aws_s3_bucket.athena_results.id}/results/"
      ATHENA_DATABASE  = "default"
      ALLOWED_ORIGIN   = var.upload_allowed_origin
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_analytics]

  tags = local.common_tags
}

resource "aws_apigatewayv2_api" "upload_api" {
  name          = "${local.name_prefix}-upload-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [var.upload_allowed_origin]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 300
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_integration" "upload_lambda" {
  api_id                 = aws_apigatewayv2_api.upload_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.upload_handler.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 15000
}

resource "aws_apigatewayv2_route" "upload_url" {
  api_id    = aws_apigatewayv2_api.upload_api.id
  route_key = "POST /v1/files/upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.upload_lambda.id}"
}

resource "aws_apigatewayv2_route" "upload_compat" {
  api_id    = aws_apigatewayv2_api.upload_api.id
  route_key = "POST /v1/files/upload"
  target    = "integrations/${aws_apigatewayv2_integration.upload_lambda.id}"
}

resource "aws_apigatewayv2_integration" "analytics_lambda" {
  api_id                 = aws_apigatewayv2_api.upload_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.analytics_handler.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 20000
}

resource "aws_apigatewayv2_route" "analytics_health" {
  api_id    = aws_apigatewayv2_api.upload_api.id
  route_key = "GET /v1/analytics/health"
  target    = "integrations/${aws_apigatewayv2_integration.analytics_lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.upload_api.id
  name        = "$default"
  auto_deploy = true

  tags = local.common_tags
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.upload_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "apigw_invoke_analytics" {
  statement_id  = "AllowExecutionFromApiGatewayAnalytics"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analytics_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.upload_api.execution_arn}/*/*"
}

# -----------------------------
# CloudTrail
# -----------------------------
resource "aws_s3_bucket" "cloudtrail" {
  bucket = local.trail_bucket_name

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cloudtrail"
  })
}

resource "aws_s3_bucket_versioning" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "cloudtrail_bucket" {
  statement {
    sid    = "AWSCloudTrailAclCheck"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.cloudtrail.arn]
  }

  statement {
    sid    = "AWSCloudTrailWrite"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.cloudtrail.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    ]

    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  policy = data.aws_iam_policy_document.cloudtrail_bucket.json
}

resource "aws_cloudtrail" "main" {
  name                          = "${local.name_prefix}-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_logging                = true

  depends_on = [aws_s3_bucket_policy.cloudtrail]

  tags = local.common_tags
}

# -----------------------------
# CloudWatch (기본 알람)
# -----------------------------
resource "aws_cloudwatch_metric_alarm" "fe_cpu_high" {
  alarm_name          = "${local.name_prefix}-fe-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "FE EC2 CPU > 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.fe.id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "be_cpu_high" {
  alarm_name          = "${local.name_prefix}-be-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "BE EC2 CPU > 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.be.id
  }

  tags = local.common_tags
}
