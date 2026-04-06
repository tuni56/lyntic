locals {
  lambda_name = "AFLD-Orchestrator"
  dlq_name    = "lyntic-dlq"
  bedrock_model = "anthropic.claude-sonnet-4-6"
}

resource "aws_cloudwatch_dashboard" "afld" {
  dashboard_name = "AFLD-Performance"

  dashboard_body = jsonencode({
    widgets = [
      # ── Lambda: Invocations vs Errors ──────────────────────────────────────
      {
        type   = "metric"
        x = 0; y = 0; width = 12; height = 6
        properties = {
          title  = "Lambda — Invocations vs Errors"
          region = var.aws_region
          stat   = "Sum"
          period = 60
          metrics = [
            ["AWS/Lambda", "Invocations",    "FunctionName", local.lambda_name],
            ["AWS/Lambda", "Errors",         "FunctionName", local.lambda_name, { color = "#d62728" }]
          ]
        }
      },
      # ── Lambda: Concurrency vs Throttles ──────────────────────────────────
      {
        type   = "metric"
        x = 12; y = 0; width = 12; height = 6
        properties = {
          title  = "Lambda — Concurrency vs Throttles"
          region = var.aws_region
          stat   = "Maximum"
          period = 60
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", local.lambda_name],
            ["AWS/Lambda", "Throttles",            "FunctionName", local.lambda_name, { color = "#ff7f0e" }]
          ]
        }
      },
      # ── Bedrock: Invocation Latency (avg + p99) ────────────────────────────
      {
        type   = "metric"
        x = 0; y = 6; width = 12; height = 6
        properties = {
          title  = "Bedrock — Invocation Latency (avg & p99)"
          region = var.aws_region
          period = 60
          metrics = [
            ["AWS/Bedrock", "InvocationLatency", "ModelId", local.bedrock_model, { stat = "Average", label = "avg" }],
            ["AWS/Bedrock", "InvocationLatency", "ModelId", local.bedrock_model, { stat = "p99",     label = "p99", color = "#9467bd" }]
          ]
        }
      },
      # ── SQS DLQ Depth ─────────────────────────────────────────────────────
      {
        type   = "metric"
        x = 12; y = 6; width = 12; height = 6
        properties = {
          title  = "DLQ — Failed Audit Depth"
          region = var.aws_region
          stat   = "Maximum"
          period = 60
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", local.dlq_name, { color = "#d62728" }]
          ]
        }
      }
    ]
  })
}
