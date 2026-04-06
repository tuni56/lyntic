data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "permissions" {
  statement {
    sid     = "BedrockInvoke"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-sonnet-4-6"
    ]
  }

  statement {
    sid     = "KinesisConsume"
    actions = ["kinesis:GetRecords", "kinesis:GetShardIterator",
               "kinesis:DescribeStream", "kinesis:ListShards"]
    resources = [aws_kinesis_stream.ingestion.arn]
  }

  statement {
    sid       = "SNSPublish"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.leak_alerts.arn]
  }

  statement {
    sid       = "S3Write"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.traces.arn}/*"]
  }

  statement {
    sid     = "Logs"
    actions = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${var.project}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = { Stage = "Horizon-1" }
}

resource "aws_iam_role_policy" "lambda_policy" {
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.permissions.json
}
