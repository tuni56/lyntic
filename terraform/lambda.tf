data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/../lambda.zip"
}

resource "aws_lambda_function" "auditor" {
  function_name    = "${var.project}-auditor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 270
  tags             = { Stage = "Horizon-1" }

  environment {
    variables = {
      DYNAMO_TABLE  = aws_dynamodb_table.flags.name
      S3_BUCKET     = aws_s3_bucket.traces.bucket
      BEDROCK_MODEL = "anthropic.claude-sonnet-4-6"
    }
  }
}
