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
    [k3s]
    ${aws_eip.app.public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/agentic-ids
  EOT
}

output "alerts_topic_arn" {
  description = "SNS topic that receives CloudWatch alarm notifications"
  value       = aws_sns_topic.alerts.arn
}

output "cpu_alarm_name" {
  description = "Name of the high-CPU CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.cpu_high.alarm_name
}
