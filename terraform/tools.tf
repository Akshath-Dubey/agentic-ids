# Tools server: Prometheus, Alertmanager, Grafana and SonarQube (Docker Compose).

resource "aws_security_group" "tools" {
  name        = "${var.instance_name}-tools-sg"
  description = "Agentic IDS tools: Grafana, SonarQube (public); Prometheus/Alertmanager (admin IPs)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }

  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # GitHub-hosted runners upload analysis results here, so it must be reachable.
  ingress {
    description = "SonarQube"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Prometheus UI (admin IPs only)"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = var.admin_cidrs
  }

  ingress {
    description = "Alertmanager UI (admin IPs only)"
    from_port   = 9093
    to_port     = 9093
    protocol    = "tcp"
    cidr_blocks = var.admin_cidrs
  }

  egress {
    description = "All outbound (scraping, image pulls, SMTP)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.instance_name}-tools-sg"
  }
}

resource "aws_instance" "tools" {
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu.id
  instance_type          = var.tools_instance_type
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.tools.id]

  root_block_device {
    volume_type = "gp3"
    volume_size = var.tools_volume_size
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required"
  }

  tags = {
    Name = "${var.instance_name}-tools"
    Role = "monitoring-sonarqube"
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

resource "aws_eip" "tools" {
  instance = aws_instance.tools.id
  domain   = "vpc"

  tags = {
    Name = "${var.instance_name}-tools-eip"
  }
}
