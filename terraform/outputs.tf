output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Elastic IP of the instance (use as the EC2_HOST GitHub secret)"
  value       = aws_eip.app.public_ip
}

output "public_dns" {
  description = "Public DNS name of the instance"
  value       = aws_eip.app.public_dns
}

output "app_url" {
  description = "Agentic IDS dashboard URL"
  value       = "http://${aws_eip.app.public_ip}"
}

output "ssh_user" {
  description = "SSH user for the Ubuntu AMI"
  value       = "ubuntu"
}

output "ssh_command" {
  description = "SSH command for manual access"
  value       = "ssh -i ~/.ssh/agentic-ids ubuntu@${aws_eip.app.public_ip}"
}

output "ansible_inventory" {
  description = "Contents for ansible/inventory.ini"
  value       = <<-EOT
    [k3s_server]
    ${aws_eip.app.public_ip} private_ip=${aws_instance.app.private_ip}

    [k3s_agents]
    ${join("\n", [for w in aws_instance.worker : "${w.public_ip} private_ip=${w.private_ip}"])}

    [monitoring]
    ${aws_eip.tools.public_ip} private_ip=${aws_instance.tools.private_ip}

    [all:vars]
    ansible_user=ubuntu
    ansible_ssh_private_key_file=~/.ssh/agentic-ids
    app_public_ip=${aws_eip.app.public_ip}
    tools_public_ip=${aws_eip.tools.public_ip}
    alert_email=${var.alert_email}
  EOT
}

output "worker_public_ips" {
  description = "Public IPs of the K3s worker nodes (not static)"
  value       = aws_instance.worker[*].public_ip
}

output "tools_public_ip" {
  description = "Elastic IP of the tools server"
  value       = aws_eip.tools.public_ip
}

output "grafana_url" {
  description = "Grafana dashboards"
  value       = "http://${aws_eip.tools.public_ip}:3000"
}

output "sonarqube_url" {
  description = "SonarQube (also the SONAR_HOST_URL GitHub variable)"
  value       = "http://${aws_eip.tools.public_ip}:9000"
}

output "prometheus_url" {
  description = "Prometheus UI (admin_cidrs only)"
  value       = "http://${aws_eip.tools.public_ip}:9090"
}

output "alertmanager_url" {
  description = "Alertmanager UI (admin_cidrs only)"
  value       = "http://${aws_eip.tools.public_ip}:9093"
}

output "alerts_topic_arn" {
  description = "SNS topic for CloudWatch alarms (only when enable_cloudwatch_alerts = true)"
  value       = one(aws_sns_topic.alerts[*].arn)
}
