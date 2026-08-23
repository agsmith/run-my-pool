locals {
  ecs_services = {
    backend = {
      service_name     = aws_ecs_service.backend.name
      target_group_arn = aws_lb_target_group.backend.arn
      target_suffix    = aws_lb_target_group.backend.arn_suffix
    }
    frontend = {
      service_name     = aws_ecs_service.frontend.name
      target_group_arn = aws_lb_target_group.frontend.arn
      target_suffix    = aws_lb_target_group.frontend.arn_suffix
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  for_each = local.ecs_services

  alarm_name          = "runmypool-ecs-${each.key}-cpu-high"
  alarm_description   = "${each.key} ECS CPU exceeded 80% for 10 minutes. Autoscaling should respond; investigate if sustained."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = each.value.service_name
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  for_each = local.ecs_services

  alarm_name          = "runmypool-ecs-${each.key}-memory-high"
  alarm_description   = "${each.key} ECS memory exceeded 80% for 10 minutes. Autoscaling should respond; investigate leaks or sustained load."
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = each.value.service_name
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_running_tasks_low" {
  for_each = local.ecs_services

  alarm_name          = "runmypool-ecs-${each.key}-running-tasks-low"
  alarm_description   = "${each.key} has no running ECS task. The service is unavailable until ECS replaces it."
  namespace           = "ECS/ContainerInsights"
  metric_name         = "RunningTaskCount"
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = each.value.service_name
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_scaled_out" {
  for_each = local.ecs_services

  alarm_name          = "runmypool-ecs-${each.key}-scaled-out"
  alarm_description   = "${each.key} ECS autoscaling increased desired capacity above the normal one-task baseline. An OK notification means it scaled back to one."
  namespace           = "ECS/ContainerInsights"
  metric_name         = "DesiredTaskCount"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 1
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = each.value.service_name
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  for_each = local.ecs_services

  alarm_name          = "runmypool-alb-${each.key}-unhealthy-targets"
  alarm_description   = "The ${each.key} load balancer target is unhealthy. Requests may fail until ECS or the health check recovers."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  treat_missing_data  = "breaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = each.value.target_suffix
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_target_5xx" {
  for_each = local.ecs_services

  alarm_name          = "runmypool-alb-${each.key}-target-5xx"
  alarm_description   = "The ${each.key} target returned at least five HTTP 5xx responses in five minutes."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 5
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = each.value.target_suffix
  }

  alarm_actions = [aws_sns_topic.result_updater_alerts.arn]
  ok_actions    = [aws_sns_topic.result_updater_alerts.arn]
}
