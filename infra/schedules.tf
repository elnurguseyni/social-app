resource "aws_iam_role" "scheduled_operations" {
  name = "social-app-scheduled-operations"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "scheduled_operations" {
  name = "social-app-scheduled-operations"
  role = aws_iam_role.scheduled_operations.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
        ]
        Resource = aws_ecs_service.app.id
      },
      {
        Effect = "Allow"
        Action = [
          "rds:StartDBInstance",
          "rds:StopDBInstance",
          "rds:DescribeDBInstances"
        ]
        Resource = aws_db_instance.app.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:DisableAlarmActions",
          "cloudwatch:EnableAlarmActions",
          "cloudwatch:DisableAlarmActions",
          "cloudwatch:EnableAlarmActions",
          "cloudwatch:DescribeAlarms"
        ]
        Resource = aws_cloudwatch_metric_alarm.ecs_running_tasks.arn
      }
    ]
  })
}

resource "aws_sfn_state_machine" "morning_start" {
  name     = "social-app-morning-start"
  role_arn = aws_iam_role.scheduled_operations.arn
  type     = "STANDARD"

  definition = jsonencode({
    StartAt        = "CheckDatabase"
    TimeoutSeconds = 7200

    States = {
      CheckDatabase = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:rds:describeDBInstances"
        Parameters = {
          DbInstanceIdentifier = aws_db_instance.app.identifier
        }
        Next = "DatabaseStatus"
      }

      DatabaseStatus = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.DbInstances[0].DbInstanceStatus"
            StringEquals = "available"
            Next         = "StartEcs"
          },
          {
            Variable     = "$.DbInstances[0].DbInstanceStatus"
            StringEquals = "stopped"
            Next         = "StartDatabase"
          }
        ]
        Default = "WaitForDatabase"
      }

      StartDatabase = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:rds:startDBInstance"
        Parameters = {
          DbInstanceIdentifier = aws_db_instance.app.identifier
        }
        Next = "WaitForDatabase"
      }

      WaitForDatabase = {
        Type    = "Wait"
        Seconds = 60
        Next    = "CheckDatabase"
      }

      StartEcs = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:ecs:updateService"
        Parameters = {
          Cluster      = aws_ecs_cluster.app.arn
          Service      = aws_ecs_service.app.name
          DesiredCount = 1
        }
        Next = "WaitForApp"
      }
      WaitForApp = {
        Type    = "Wait"
        Seconds = 60
        Next    = "CheckAppAlarm"
      }

      CheckAppAlarm = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:cloudwatch:describeAlarms"
        Parameters = {
          AlarmNames = [
            aws_cloudwatch_metric_alarm.ecs_running_tasks.alarm_name
          ]
          AlarmTypes = ["MetricAlarm"]
        }
        Next = "AppHealthy"
      }

      AppHealthy = {
        Type = "Choice"
        Choices = [{
          Variable     = "$.MetricAlarms[0].StateValue"
          StringEquals = "OK"
          Next         = "EnableAppAlarm"
        }]
        Default = "WaitForApp"
      }

      EnableAppAlarm = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:cloudwatch:enableAlarmActions"
        Parameters = {
          AlarmNames = [
            aws_cloudwatch_metric_alarm.ecs_running_tasks.alarm_name
          ]
        }
        End = true
      }
    }
  })

  depends_on = [aws_iam_role_policy.scheduled_operations]
}

resource "aws_sfn_state_machine" "evening_stop" {
  name     = "social-app-evening-stop"
  role_arn = aws_iam_role.scheduled_operations.arn
  type     = "STANDARD"

  definition = jsonencode({
    StartAt        = "MuteAppAlarm"
    TimeoutSeconds = 7200

    States = {
      MuteAppAlarm = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:cloudwatch:disableAlarmActions"
        Parameters = {
          AlarmNames = [
            aws_cloudwatch_metric_alarm.ecs_running_tasks.alarm_name
          ]
        }
        Next = "StopEcs"
      }
      StopEcs = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:ecs:updateService"
        Parameters = {
          Cluster      = aws_ecs_cluster.app.arn
          Service      = aws_ecs_service.app.name
          DesiredCount = 0
        }
        Next = "WaitForEcs"
      }

      WaitForEcs = {
        Type    = "Wait"
        Seconds = 30
        Next    = "CheckEcs"
      }

      CheckEcs = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:ecs:describeServices"
        Parameters = {
          Cluster  = aws_ecs_cluster.app.arn
          Services = [aws_ecs_service.app.name]
        }
        Next = "EcsStopped"
      }

      EcsStopped = {
        Type = "Choice"
        Choices = [{
          And = [
            {
              Variable      = "$.Services[0].DesiredCount"
              NumericEquals = 0
            },
            {
              Variable      = "$.Services[0].RunningCount"
              NumericEquals = 0
            },
            {
              Variable      = "$.Services[0].PendingCount"
              NumericEquals = 0
            }
          ]
          Next = "CheckDatabase"
        }]
        Default = "WaitForEcs"
      }
      CheckDatabase = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:rds:describeDBInstances"
        Parameters = {
          DbInstanceIdentifier = aws_db_instance.app.identifier
        }
        Next = "DatabaseStatus"
      }

      DatabaseStatus = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.DbInstances[0].DbInstanceStatus"
            StringEquals = "available"
            Next         = "StopDatabase"
          },
          {
            Variable     = "$.DbInstances[0].DbInstanceStatus"
            StringEquals = "stopped"
            Next         = "Finished"
          }
        ]
        Default = "WaitForDatabase"
      }

      StopDatabase = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:rds:stopDBInstance"
        Parameters = {
          DbInstanceIdentifier = aws_db_instance.app.identifier
        }
        Next = "WaitForDatabase"
      }

      WaitForDatabase = {
        Type    = "Wait"
        Seconds = 60
        Next    = "CheckDatabase"
      }

      Finished = {
        Type = "Succeed"
      }
    }
  })

  depends_on = [aws_iam_role_policy.scheduled_operations]
}

resource "aws_cloudwatch_event_rule" "scheduled_operations_failed" {
  name        = "social-app-scheduled-operations-failed"
  description = "Detect unsuccessful morning or evening workflows"

  event_pattern = jsonencode({
    source        = ["aws.states"]
    "detail-type" = ["Step Functions Execution Status Change"]
    detail = {
      stateMachineArn = [
        aws_sfn_state_machine.morning_start.arn,
        aws_sfn_state_machine.evening_stop.arn
      ]
      status = ["FAILED", "TIMED_OUT", "ABORTED"]
    }
  })
}

resource "aws_cloudwatch_event_target" "scheduled_operations_alert" {
  rule      = aws_cloudwatch_event_rule.scheduled_operations_failed.name
  target_id = "SendToAlerts"
  arn       = aws_sns_topic.alerts.arn

  input_transformer {
    input_paths = {
      execution = "$.detail.executionArn"
      status    = "$.detail.status"
    }
    input_template = "\"Social app scheduled operation <status>. Execution: <execution>. Check the workflow, app availability, and whether app-health alarm actions need re-enabling.\""
  }
}

resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "PreserveExistingAccountAccess"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action = [
          "SNS:GetTopicAttributes",
          "SNS:SetTopicAttributes",
          "SNS:AddPermission",
          "SNS:RemovePermission",
          "SNS:DeleteTopic",
          "SNS:Subscribe",
          "SNS:ListSubscriptionsByTopic",
          "SNS:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
        Condition = {
          StringEquals = {
            "AWS:SourceOwner" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AllowEventBridgeNotifications"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}

resource "aws_scheduler_schedule_group" "app" {
  name = "social-app"
}

resource "aws_iam_role" "scheduler" {
  name = "social-app-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          "aws:SourceArn"     = aws_scheduler_schedule_group.app.arn
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "social-app-start-workflows"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "states:StartExecution"
      Resource = [
        aws_sfn_state_machine.morning_start.arn,
        aws_sfn_state_machine.evening_stop.arn
      ]
    }]
  })
}
resource "aws_scheduler_schedule" "app" {
  for_each = {
    evening = {
      expression = "cron(0 1 * * ? *)"
      workflow   = aws_sfn_state_machine.evening_stop.arn
    }
    morning = {
      expression = "cron(0 9 * * ? *)"
      workflow   = aws_sfn_state_machine.morning_start.arn
    }
  }

  name                         = "social-app-${each.key}"
  group_name                   = aws_scheduler_schedule_group.app.name
  schedule_expression          = each.value.expression
  schedule_expression_timezone = "Europe/Vilnius"
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = each.value.workflow
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({})

    retry_policy {
      maximum_event_age_in_seconds = 300
      maximum_retry_attempts       = 3
    }
  }

  depends_on = [aws_iam_role_policy.scheduler]
}