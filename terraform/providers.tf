terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Credentials come from the standard AWS chain (env vars / ~/.aws/credentials).
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "agentic-ids"
      ManagedBy = "terraform"
    }
  }
}
