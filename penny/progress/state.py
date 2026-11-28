"""Fixed public vocabulary; no names, arbitrary text or source identifiers."""
import json
from hashlib import sha256

SCHEMA="penny-progress-v1"
MAX_AGE=3600
MAX_VALUE=9_000_000_000_000_000
FINANCE_KEYS=("commercial_receipts","commercial_refunds","community_support",
    "founder_cash_funding","founder_paid_costs","operating_expenses","payment_fees",
    "commercial_result_after_recorded_costs","matched_cash","statement_at")
BUSINESS_KEYS=("proposed","approved","started","overdue","expired","rejected",
               "stopped","measured_target_met","measured_target_missed")


def validate(payload):
    # Explicit exact types and allowlist; even a corrupted cached row must
    # never expose arbitrary JSON keys or free text through the reader.
    if type(payload) is not dict or set(payload)!={"schema","finance","business"} or payload["schema"]!=SCHEMA:
        raise ValueError("invalid projection schema")
    for name,keys in (("finance",FINANCE_KEYS),("business",BUSINESS_KEYS)):
        data=payload[name]
        if data is None:
            continue
        if type(data) is not dict or set(data)!=set(keys):
            raise ValueError("invalid projection section")
        for key,value in data.items():
            if type(value) is not int or abs(value)>MAX_VALUE:
                raise ValueError("invalid projection value")
            if key!="commercial_result_after_recorded_costs" and value<0:
                raise ValueError("unexpected negative metric")
        if name=="finance" and data["statement_at"]<=0:
            raise ValueError("missing statement timestamp")
    return payload


def digest(payload):
    return sha256(json.dumps(validate(payload),sort_keys=True,
        separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest()
