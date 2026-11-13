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

variable "alert_email" {
  description = "Email address that receives CloudWatch alarm notifications. Leave empty to create the alarms without an email subscription."
  type        = string
  default     = ""
}

variable "cpu_alarm_threshold" {
  description = "Average CPU percentage (over 5 minutes) that triggers the high-CPU alert."
  type        = number
  default     = 80
}

variable "enable_cloudwatch_alerts" {
  description = "Create the CloudWatch/SNS email alarms (needs sns:* and cloudwatch alarm permissions on the IAM user). Prometheus Alertmanager emails CPU alerts independently."
  type        = bool
  default     = false
}

variable "worker_count" {
  description = "Number of K3s worker (agent) nodes."
  type        = number
  default     = 1
}

variable "worker_instance_type" {
  description = "EC2 instance type for K3s worker nodes."
  type        = string
  default     = "t3.small"
}

variable "tools_instance_type" {
  description = "EC2 instance type for the Prometheus/Grafana/SonarQube server. SonarQube needs ~2 GiB on its own, so 4 GiB (t3.medium or c7i-flex.large on Free Tier accounts) is the minimum."
  type        = string
  default     = "c7i-flex.large"
}

variable "tools_volume_size" {
  description = "Root volume size (GiB) for the tools server."
  type        = number
  default     = 30
}

variable "admin_cidrs" {
  description = "CIDRs allowed to open the Prometheus (9090) and Alertmanager (9093) UIs. Grafana and SonarQube have their own logins and are public."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
