import json, os, uuid, boto3
from datetime import datetime, timezone

bedrock  = boto3.client("bedrock-runtime")
dynamo   = boto3.resource("dynamodb").Table(os.environ["DYNAMO_TABLE"])
s3       = boto3.client("s3")
MODEL_ID = os.environ["BEDROCK_MODEL"]
BUCKET   = os.environ["S3_BUCKET"]


def lambda_handler(event, context):
    for record in event["Records"]:
        transaction = json.loads(record["body"])
        trace_id    = str(uuid.uuid4())
        ts          = int(datetime.now(timezone.utc).timestamp())

        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
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

        result   = json.loads(response["body"].read())
        analysis = json.loads(result["content"][0]["text"])

        # Full trace → S3 (always)
        s3.put_object(
            Bucket=BUCKET,
            Key=f"traces/{trace_id}.json",
            Body=json.dumps({
                "transaction": transaction,
                "analysis":    analysis,
                "trace_id":    trace_id,
                "timestamp":   ts
            })
        )

        # Flagged → DynamoDB (always write for audit trail)
        dynamo.put_item(Item={
            "transaction_id": trace_id,
            "timestamp":      ts,
            "customer_id":    transaction.get("customer_id", "unknown"),
            "tx_id":          transaction.get("id", "unknown"),
            "flagged":        analysis.get("flagged", False),
            "reason":         analysis.get("reason", ""),
        })
