import json, os, uuid, base64, boto3
from datetime import datetime, timezone

bedrock   = boto3.client("bedrock-runtime")
s3        = boto3.client("s3")
sns       = boto3.client("sns")
MODEL_ID  = os.environ["BEDROCK_MODEL"]
BUCKET    = os.environ["S3_BUCKET"]
SNS_TOPIC = os.environ["SNS_TOPIC_ARN"]


def analyze(transaction: dict) -> dict:
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 256,
            "messages": [{
                "role": "user",
                "content": (
                    "Analyze this financial transaction for leaks, anomalies, or fraud. "
                    "Reply ONLY with JSON: {\"flagged\": bool, \"reason\": str}.\n\n"
                    f"{json.dumps(transaction)}"
                )
            }]
        })
    )
    result = json.loads(response["body"].read())
    return json.loads(result["content"][0]["text"])


def lambda_handler(event, context):
    for record in event["Records"]:
        # Kinesis records are base64-encoded
        transaction = json.loads(base64.b64decode(record["kinesis"]["data"]))
        trace_id    = str(uuid.uuid4())
        ts          = int(datetime.now(timezone.utc).timestamp())

        analysis = analyze(transaction)

        if analysis.get("flagged"):
            # Leak → SNS alert → high-priority SQS
            sns.publish(
                TopicArn=SNS_TOPIC,
                Subject="AFLD: Leak Detected",
                Message=json.dumps({
                    "trace_id":    trace_id,
                    "timestamp":   ts,
                    "transaction": transaction,
                    "reason":      analysis["reason"],
                })
            )
        else:
            # Clean → S3 audit log
            s3.put_object(
                Bucket=BUCKET,
                Key=f"audit/{trace_id}.json",
                Body=json.dumps({
                    "trace_id":    trace_id,
                    "timestamp":   ts,
                    "transaction": transaction,
                    "analysis":    analysis,
                })
            )
