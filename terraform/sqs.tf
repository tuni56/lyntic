# ── Kinesis Data Stream ───────────────────────────────────────────────────────
resource "aws_kinesis_stream" "ingestion" {
  name             = "${var.project}-stream"
  shard_count      = 1
  retention_period = 24
  tags             = { Stage = "Horizon-1" }
}

# ── Kinesis → Lambda trigger ──────────────────────────────────────────────────
resource "aws_lambda_event_source_mapping" "kinesis_trigger" {
  event_source_arn  = aws_kinesis_stream.ingestion.arn
  function_name     = aws_lambda_function.auditor.arn
  starting_position = "LATEST"
  batch_size        = 10
}

# ── SNS topic (leak alerts) ───────────────────────────────────────────────────
resource "aws_sns_topic" "leak_alerts" {
  name = "${var.project}-leak-alerts"
  tags = { Stage = "Horizon-1" }
}

# ── High-priority SQS + subscription ─────────────────────────────────────────
resource "aws_sqs_queue" "high_priority" {
  name                       = "${var.project}-high-priority"
  visibility_timeout_seconds = 300
  tags                       = { Stage = "Horizon-1" }
}

resource "aws_sns_topic_subscription" "leak_to_sqs" {
  topic_arn = aws_sns_topic.leak_alerts.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.high_priority.arn
}

resource "aws_sqs_queue_policy" "allow_sns" {
  queue_url = aws_sqs_queue.high_priority.url
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sns.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.high_priority.arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.leak_alerts.arn } }
    }]
  })
}

# ── DLQ (kept for Lambda failures) ───────────────────────────────────────────
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.project}-dlq"
  message_retention_seconds = 1209600
  tags                      = { Stage = "Horizon-1" }
}
