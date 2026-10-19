"""Synthetic snapshot demo; standard library only, not an Informatica runtime."""
import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def unique(rows, keys):
    result = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        if key in result and result[key] != row:
            raise ValueError(f"Conflicting source key: {key}")
        result[key] = row
    return list(result.values())


def build(customers, orders):
    # Input is a COMPLETE snapshot, not a change feed. Identity requires a trusted
    # synthetic loyalty ID. Email alone is never sufficient to merge customers.
    customers = unique(customers, ("source", "customer_id"))
    orders = unique(orders, ("source", "order_id"))
    groups, email_ids = defaultdict(list), defaultdict(set)
    rejects = []
    for r in customers:
        if r["source"] not in ("crm", "shop"):
            raise ValueError("Unsupported customer source")
        email = r["email"].strip().lower()
        if r["loyalty_id"]:
            email_ids[email].add(r["loyalty_id"])
    for r in customers:
        email = r["email"].strip().lower()
        reason = None
        if not r["loyalty_id"]:
            reason = "MISSING_TRUSTED_ID"
        elif not email or "@" not in email:
            reason = "INVALID_EMAIL"
        elif len(email_ids[email]) > 1:
            reason = "EMAIL_ID_CONFLICT"
        if reason:
            rejects.append({"entity":"customer", "source":r["source"], "key":r["customer_id"], "reason":reason})
        else:
            groups[r["loyalty_id"]].append(r)
    golden, crosswalk = [], []
    for loyalty_id, rows in sorted(groups.items()):
        # Stable only while trusted ID remains stable. Production uses MDM IDs.
        gid = "G_" + hashlib.sha256(loyalty_id.encode()).hexdigest()[:20]
        winner = sorted(rows, key=lambda r: (0 if r["source"] == "crm" else 1, r["customer_id"]))[0]
        golden.append({"golden_id":gid, "name":winner["name"], "region":winner["region"], "survivor_source":winner["source"]})
        crosswalk.extend({"source":r["source"], "customer_id":r["customer_id"], "golden_id":gid} for r in rows)
    lookup = {(r["source"],r["customer_id"]):r["golden_id"] for r in crosswalk}
    facts = []
    for r in orders:
        gid = lookup.get((r["source"],r["customer_id"]))
        reason = None
        if r["currency"] != "USD":
            reason = "UNSUPPORTED_CURRENCY"
        elif type(r["amount_cents"]) is not int or r["amount_cents"] < 0:
            reason = "INVALID_AMOUNT"
        elif gid is None:
            reason = "UNRESOLVED_CUSTOMER"
        if reason:
            rejects.append({"entity":"order", "source":r["source"], "key":r["order_id"], "reason":reason})
        else:
            facts.append({"source":r["source"], "order_id":r["order_id"], "golden_id":gid, "amount_cents":r["amount_cents"], "currency":r["currency"]})
    return {"dim_customer":golden, "customer_crosswalk":sorted(crosswalk,key=lambda r:(r["source"],r["customer_id"])),
            "fact_order":sorted(facts,key=lambda r:(r["source"],r["order_id"])),
            "exceptions":sorted(rejects,key=lambda r:(r["entity"],r["source"],r["key"]))}


if __name__ == "__main__":
    data = json.loads(Path("data/sample.json").read_text())
    result = build(data["customers"], [])
    Path("output").mkdir(exist_ok=True)
    Path("output/mastering.json").write_text(json.dumps(result,indent=2))
    print(json.dumps({k:len(v) for k,v in result.items()},indent=2))
