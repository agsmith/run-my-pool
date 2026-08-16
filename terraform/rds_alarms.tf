# Early-warning alarms for resource pressure on the production RDS instance.
# Every alarm sends both ALARM and recovery notifications to the confirmed
# support@runmypool.net subscription on the shared operations SNS topic.

locals {
  rds_resource_alarms = {
    cpu_high = {
      metric_name         = "CPUUtilization"
      comparison_operator = "GreaterThanThreshold"
      threshold           = 70
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 3
      unit                = "Percent"
      description         = "RDS CPU averaged more than 70% for 15 minutes. Review database load and slow queries; scale the instance if sustained."
    }
    connections_high = {
      metric_name         = "DatabaseConnections"
      comparison_operator = "GreaterThanThreshold"
      threshold           = 65
      statistic           = "Maximum"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 2
      unit                = "Count"
      description         = "RDS exceeded 65 concurrent connections in 2 of 3 five-minute periods, approaching the db.t3.micro connection ceiling."
    }
    memory_low = {
      metric_name         = "FreeableMemory"
      comparison_operator = "LessThanThreshold"
      threshold           = 134217728 # 128 MiB
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 3
      unit                = "Bytes"
      description         = "RDS freeable memory remained below 128 MiB for 15 minutes. Check swapping and query load; instance scaling may be required."
    }
    swap_high = {
      metric_name         = "SwapUsage"
      comparison_operator = "GreaterThanThreshold"
      threshold           = 268435456 # 256 MiB
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 3
      unit                = "Bytes"
      description         = "RDS swap usage remained above 256 MiB for 15 minutes, indicating sustained memory pressure."
    }
    storage_low = {
      metric_name         = "FreeStorageSpace"
      comparison_operator = "LessThanThreshold"
      threshold           = 5368709120 # 5 GiB
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 3
      unit                = "Bytes"
      description         = "RDS free storage remained below 5 GiB for 15 minutes. Increase allocated storage before writes are interrupted."
    }
    cpu_credits_low = {
      metric_name         = "CPUCreditBalance"
      comparison_operator = "LessThanThreshold"
      threshold           = 50
      statistic           = "Minimum"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 3
      unit                = "Count"
      description         = "RDS burst CPU credit balance remained below 50 for 15 minutes. Sustained load may throttle the burstable instance."
    }
    burst_balance_low = {
      metric_name         = "BurstBalance"
      comparison_operator = "LessThanThreshold"
      threshold           = 20
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 3
      unit                = "Percent"
      description         = "RDS gp2 storage burst balance remained below 20% for 15 minutes. Storage I/O throttling is imminent."
    }
    read_latency_high = {
      metric_name         = "ReadLatency"
      comparison_operator = "GreaterThanThreshold"
      threshold           = 0.05
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 2
      unit                = "Seconds"
      description         = "RDS average read latency exceeded 50 ms in 2 of 3 five-minute periods. Investigate query and storage pressure."
    }
    write_latency_high = {
      metric_name         = "WriteLatency"
      comparison_operator = "GreaterThanThreshold"
      threshold           = 0.05
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 2
      unit                = "Seconds"
      description         = "RDS average write latency exceeded 50 ms in 2 of 3 five-minute periods. Investigate query and storage pressure."
    }
    disk_queue_high = {
      metric_name         = "DiskQueueDepth"
      comparison_operator = "GreaterThanThreshold"
      threshold           = 5
      statistic           = "Average"
      period              = 300
      evaluation_periods  = 3
      datapoints_to_alarm = 2
      unit                = "Count"
      description         = "RDS disk queue depth exceeded 5 in 2 of 3 five-minute periods, indicating storage contention."
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_resource_pressure" {
  for_each = local.rds_resource_alarms

  alarm_name          = "runmypool-rds-${replace(each.key, "_", "-")}"
  alarm_description   = each.value.description
  namespace           = "AWS/RDS"
  metric_name         = each.value.metric_name
  comparison_operator = each.value.comparison_operator
  threshold           = each.value.threshold
  statistic           = each.value.statistic
  period              = each.value.period
  evaluation_periods  = each.value.evaluation_periods
  datapoints_to_alarm = each.value.datapoints_to_alarm
  unit                = each.value.unit
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.identifier
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]

  tags = merge(local.common_tags, {
    Component = "database"
  })
}
