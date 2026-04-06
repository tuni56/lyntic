#!/usr/bin/env python3
"""
AFLD Stress-Test — Synthetic payload generator (Kinesis target)
Usage: uv run load_generator.py
"""
import json, uuid, time, random, boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
STREAM_NAME = "lyntic-stream"
TOTAL       = 2500
LEAK_RATIO  = 0.05
MAX_WORKERS = 75
REGION      = "us-east-2"

kinesis = boto3.client("kinesis", region_name=REGION)

# ── Payload factories ─────────────────────────────────────────────────────────
_duplicate_pool: list[str] = []

def normal_tx() -> dict:
    return {
        "transaction_id": str(uuid.uuid4()),
        "customer_id":    f"CUST-{random.randint(1000, 9999)}",
        "amount":         round(random.uniform(10, 5000), 2),
        "currency":       "USD",
        "timestamp":      int(datetime.now(timezone.utc).timestamp()),
        "type":           "normal",
    }

def leak_tx() -> dict:
    leak_kind = random.choice(["high_amount", "duplicate"])
    tx_id = str(uuid.uuid4())
    if leak_kind == "duplicate" and _duplicate_pool:
        tx_id = random.choice(_duplicate_pool)
    else:
        _duplicate_pool.append(tx_id)
    return {
        "transaction_id": tx_id,
        "customer_id":    f"CUST-{random.randint(1000, 9999)}",
        "amount":         round(random.uniform(50_001, 500_000), 2),
        "currency":       "USD",
        "timestamp":      int(datetime.now(timezone.utc).timestamp()),
        "type":           "leak",
    }

def build_payloads(n: int) -> list[dict]:
    leak_count = int(n * LEAK_RATIO)
    payloads   = [leak_tx() for _ in range(leak_count)] + \
                 [normal_tx() for _ in range(n - leak_count)]
    random.shuffle(payloads)
    return payloads

# ── Kinesis worker ────────────────────────────────────────────────────────────
def put_record(tx: dict) -> tuple[bool, str]:
    try:
        kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(tx),
            PartitionKey=tx["customer_id"]
        )
        return True, "200"
    except Exception as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code", "0")
        return False, code

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    payloads = build_payloads(TOTAL)
    ok = errors_403 = errors_429 = other_errors = 0

    print(f"[AFLD] Injecting {TOTAL} transactions → Kinesis:{STREAM_NAME}  (workers={MAX_WORKERS})")
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(put_record, tx): tx for tx in payloads}
        for fut in as_completed(futures):
            success, code = fut.result()
            if success:
                ok += 1
            elif code in ("403", "AccessDenied"):
                errors_403 += 1
            elif code in ("429", "ProvisionedThroughputExceededException"):
                errors_429 += 1
            else:
                other_errors += 1

    elapsed = time.perf_counter() - t0

    print("\n── Injection Phase Summary ──────────────────────────")
    print(f"  Total injected : {ok}/{TOTAL}")
    print(f"  Total time     : {elapsed:.2f}s")
    print(f"  Throughput     : {ok/elapsed:.1f} records/sec")
    print(f"  403 errors     : {errors_403}")
    print(f"  429 / throttle : {errors_429}")
    print(f"  Other errors   : {other_errors}")
    print("─────────────────────────────────────────────────────")

if __name__ == "__main__":
    main()
