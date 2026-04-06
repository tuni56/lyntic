# AFLD — Demo & Teardown Runbook

---

## Part 1 — Recording the Demo

### Act 1 — The Problem (60 sec)
Open with this statement:
> "Financial fraud costs companies millions annually. Traditional rule-based systems flag
> transactions after the fact. AFLD detects leaks in real time, at scale, using AI —
> before the money moves."

---

### Act 2 — Architecture Walkthrough (90 sec)
Open `architecture.md` in https://mermaid.live and walk the flow:

- **Kinesis** = ingestion at any scale
- **Lambda** = serverless, zero ops
- **Bedrock / Claude Sonnet 4.6** = AI reasoning, not just rules
- **SNS → SQS** = instant alert routing for flagged transactions
- **S3** = full audit trail for compliance

---

### Act 3 — Live Injection (2 min)
Split screen: terminal on the left, CloudWatch dashboard on the right.

Open the dashboard manually:
1. Go to https://console.aws.amazon.com → region **us-east-2**
2. Search **CloudWatch** → **Dashboards** → **AFLD-Performance**
3. Set auto-refresh to **10 seconds**

Run the stress test:
```bash
cd ~/lyntic/stress-test
uv run load_generator.py
```

Point to the dashboard widgets lighting up in real time:
- Lambda Invocations spiking
- Bedrock Latency (avg & p99)
- Throughput number in the terminal summary

---

### Act 4 — Show the Results (2 min)
After the run, open a terminal and run:

```bash
# Leak transactions routed to high-priority queue
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-2.amazonaws.com/748607162458/lyntic-high-priority \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-2

# Clean transactions stored in S3 audit log
aws s3 ls s3://lyntic-audit-logs/audit/ --region us-east-2 | wc -l

# Peek at one flagged transaction (shows Claude's reasoning)
aws sqs receive-message \
  --queue-url https://sqs.us-east-2.amazonaws.com/748607162458/lyntic-high-priority \
  --region us-east-2
```

Highlight the `reason` field in the JSON — Claude explains *why* the transaction was flagged,
not just that it was.

---

### Act 5 — Business Value Close (60 sec)
End with three numbers:

- **Cost**: Lambda + Bedrock on-demand = pay per transaction, not per server
- **Speed**: Sub-second AI detection vs. overnight batch jobs
- **Scale**: Kinesis on-demand absorbs any spike — no config change needed

---

### Recording Tips
- Use OBS or `simplescreenrecorder` (Ubuntu) for screen capture
- Set terminal font size to 18+ so it reads clearly on video
- Keep CloudWatch dashboard on 10s auto-refresh during injection
- End recording on the terminal summary printout — clean closing frame

---

## Part 2 — Teardown (Shutdown Infrastructure)

### Step 1 — Empty the S3 bucket (if it has objects)
```bash
aws s3 rm s3://lyntic-audit-logs --recursive --region us-east-2
```

### Step 2 — Destroy all Terraform-managed resources
```bash
cd ~/lyntic/terraform
terraform destroy
```
Type `yes` when prompted.

This removes:
- Kinesis stream
- Lambda function + IAM role
- SNS topic + SQS queues (main, high-priority, DLQ)
- S3 bucket + lifecycle rules
- DynamoDB table
- CloudWatch dashboard

### Step 3 — Remove the landing zone bucket (created outside Terraform)
```bash
aws s3 rb s3://afld-landing-zone --force --region us-east-2
```

---

### What is NOT deleted by Terraform
| Resource | How to remove |
|---|---|
| `afld-landing-zone` S3 bucket | Step 3 above |
| GitHub repo (tuni56/lyntic) | github.com → Settings → Delete repository |
| Bedrock model access | Console → Bedrock → Model access → Manage |
