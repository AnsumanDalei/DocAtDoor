terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  common_tags = {
    Project     = "DocAtDoor"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Preparation host only. No inbound web port is opened because the project
# currently has no supported production application server configuration.
resource "aws_security_group" "docatdoor_sg" {
  name        = "docatdoor-sg-${var.environment}"
  description = "Restricted SSH for infrastructure preparation only"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, { Name = "docatdoor-sg-${var.environment}" })
}

# Optional learning/preparation host. Ansible does not publish the dev app.
resource "aws_instance" "docatdoor_server" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.docatdoor_sg.id]

  root_block_device {
    volume_size = 16
    volume_type = "gp3"
  }

  tags = merge(local.common_tags, { Name = "docatdoor-server-${var.environment}" })
}
