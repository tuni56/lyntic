#!/usr/bin/env python3
"""
AFLD Stress-Test — Synthetic payload generator
Usage: uv run load_generator.py
"""
import json, uuid, time, random, boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
BUCKET       = "afld-landing-zone"
TOTAL        = 2500
LEAK_RATIO   = 0.05
MAX_WORKERS  = 75          # targets ~50-100 uploads/sec
REGION       = "us-east-2"

s3 = boto3.client("s3", region_name=REGION)

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
        tx_id = random.choice(_duplicate_pool)   # reuse ID within burst window
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

# ── Upload worker ─────────────────────────────────────────────────────────────
def upload(tx: dict) -> tuple[bool, int]:
    key = f"transactions/{tx['transaction_id']}.json"
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(tx))
        return True, 200
    except Exception as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code", "0")
        if code in ("403", "AccessDenied"):
            return False, 403
        if code in ("429", "SlowDown"):
            return False, 429
        return False, 0

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    payloads = build_payloads(TOTAL)
    ok = errors_403 = errors_429 = other_errors = 0

    print(f"[AFLD] Injecting {TOTAL} transactions → s3://{BUCKET}  (workers={MAX_WORKERS})")
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(upload, tx): tx for tx in payloads}
        for fut in as_completed(futures):
            success, code = fut.result()
            if success:
                ok += 1
            elif code == 403:
                errors_403 += 1
            elif code == 429:
                errors_429 += 1
            else:
                other_errors += 1

    elapsed = time.perf_counter() - t0

    print("\n── Injection Phase Summary ──────────────────────────")
    print(f"  Total uploaded : {ok}/{TOTAL}")
    print(f"  Total time     : {elapsed:.2f}s")
    print(f"  Throughput     : {ok/elapsed:.1f} uploads/sec")
    print(f"  403 errors     : {errors_403}")
    print(f"  429 errors     : {errors_429}")
    print(f"  Other errors   : {other_errors}")
    print("─────────────────────────────────────────────────────")

if __name__ == "__main__":
    main()
