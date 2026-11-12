# Email alerts: CloudWatch alarms on the EC2 instance -> SNS topic -> email.
# Uses the free basic EC2 metrics (5-minute CPU, 1-minute status checks), so
# nothing extra runs on the server.

resource "aws_sns_topic" "alerts" {
  name = "${var.instance_name}-alerts"
}

# AWS emails a confirmation link first; alerts are delivered only after it is clicked.
resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.instance_name}-cpu-above-${var.cpu_alarm_threshold}pct"
  alarm_description   = "Agentic IDS EC2 average CPU above ${var.cpu_alarm_threshold}% for 5 minutes (${aws_instance.app.id}, http://${aws_eip.app.public_ip})"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.cpu_alarm_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn] # "recovered" email
}

resource "aws_cloudwatch_metric_alarm" "status_check_failed" {
  alarm_name          = "${var.instance_name}-status-check-failed"
  alarm_description   = "Agentic IDS EC2 instance or system status check failing for 2 minutes (${aws_instance.app.id})"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.app.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "breaching" # no data usually means the instance is down
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
