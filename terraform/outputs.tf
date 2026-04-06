output "queue_url"    { value = aws_sqs_queue.main.url }
output "dlq_url"      { value = aws_sqs_queue.dlq.url }
output "dynamo_table" { value = aws_dynamodb_table.flags.name }
output "s3_bucket"    { value = aws_s3_bucket.traces.bucket }
