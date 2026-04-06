# Lyntic — Financial Leak Detector

## Project Structure

```
lyntic/
├── terraform/
│   ├── main.tf       # Provider + backend config
│   ├── variables.tf  # aws_region, project name
│   ├── sqs.tf        # Queue, DLQ, ESM
│   ├── iam.tf        # Lambda role + policy
│   ├── storage.tf    # S3 bucket + DynamoDB table
│   ├── lambda.tf     # Lambda function + zip packaging
│   └── outputs.tf
└── lambda/
    └── handler.py    # Bedrock auditor
```

## Deploy

```bash
cd terraform
terraform init
terraform apply
```

## Notes
- Bedrock model: `anthropic.claude-sonnet-4-6`
- SQS DLQ max receive count: 3
- Lambda timeout: 270s (under SQS visibility timeout of 300s)
- S3 encrypted at rest (AES256)
- DynamoDB on-demand billing
