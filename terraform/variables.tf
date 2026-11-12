variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "instance_name" {
  description = "Name tag for the EC2 instance and related resources"
  type        = string
  default     = "agentic-ids"
}

variable "instance_type" {
  description = "EC2 instance type. t3.small (2 vCPU / 2 GiB) is the cost-conscious demo default; use t3.medium for large CSV uploads."
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "AMI to use. Leave empty to use the latest Ubuntu 24.04 LTS (amd64) image from Canonical."
  type        = string
  default     = ""
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB"
  type        = number
  default     = 20
}

variable "ssh_key_name" {
  description = "Name of the EC2 key pair created from ssh_public_key_path"
  type        = string
  default     = "agentic-ids-key"
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key uploaded as the EC2 key pair"
  type        = string
  default     = "~/.ssh/agentic-ids.pub"
}

variable "ssh_allowed_cidrs" {
  description = "CIDR blocks allowed to SSH (port 22). GitHub-hosted runners deploy over SSH from changing IPs, so CI/CD needs 0.0.0.0/0; key-only auth is enforced by Ansible."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "http_allowed_cidrs" {
  description = "CIDR blocks allowed to reach the dashboard over HTTP (port 80)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
