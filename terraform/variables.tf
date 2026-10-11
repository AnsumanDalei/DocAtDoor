variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"  # Mumbai - closest to India
}

variable "ami_id" {
  description = "A current Ubuntu LTS AMI ID in the selected AWS region; supply explicitly."
  type        = string
  validation {
    condition     = can(regex("^ami-[0-9a-f]+$", var.ami_id))
    error_message = "Supply a valid AMI ID for the selected region."
  }
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"  # AWS free-tier eligible
}

variable "key_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "Your fixed public IPv4 address with /32; broad SSH CIDRs are rejected."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.ssh_allowed_cidr)) && endswith(var.ssh_allowed_cidr, "/32")
    error_message = "SSH ingress must be limited to one IPv4 address using /32."
  }
}

variable "environment" {
  description = "Deployment environment name (dev, staging, production) - used in tags/naming"
  type        = string
  default     = "dev"
}
