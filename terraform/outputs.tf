output "kinesis_stream_arn"   { value = aws_kinesis_stream.ingestion.arn }
output "sns_topic_arn"        { value = aws_sns_topic.leak_alerts.arn }
output "high_priority_sqs"    { value = aws_sqs_queue.high_priority.url }
output "dlq_url"              { value = aws_sqs_queue.dlq.url }
output "s3_bucket"            { value = aws_s3_bucket.traces.bucket }
