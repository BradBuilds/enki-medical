"""
Connect your app to Enki, end to end:

  1. check the node is up
  2. as the admin device, enroll your app as a write-only (Tier W) device
  3. as your app, send events (IDs only, never names or other identifiers)
  4. as the admin, read the events back, fetch the receipt, and verify the tamper-evident chain

    python examples/connect_app.py                       # uses ./enki-data and demo-tenant
    python examples/connect_app.py --event-type demo_clinic.record.accessed   # once you admit a library

Run from the repository root after `docker compose up`.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enki_client import EnkiClient, load_key, new_key, public_key_b64  # noqa: E402


def step(n: int, text: str) -> None:
    print(f"\n[{n}] {text}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Connect an app to Enki and send it events.")
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--data", default="enki-data", help="the node's data folder (holds the admin key)")
    ap.add_argument("--tenant", default="demo-tenant")
    ap.add_argument("--admin-id", default="admin-device")
    ap.add_argument("--app-id", default="my-app")
    ap.add_argument("--event-type", default="node.heartbeat", help="a built-in type, or one your library declares")
    a = ap.parse_args()

    admin = EnkiClient(a.url, a.admin_id, load_key(Path(a.data) / "keys" / "admin_device.pem"), a.tenant)

    step(1, "Node health")
    print("   ", admin.health())

    step(2, f"Enroll '{a.app_id}' as a write-only device for tenant '{a.tenant}'")
    app_key_path = Path(a.data) / "keys" / f"{a.app_id}.pem"
    if app_key_path.exists():
        app_key = load_key(app_key_path)
        print(f"    using existing key {app_key_path}")
    else:
        app_key = new_key(app_key_path)
        r = admin.enroll_device(a.app_id, public_key_b64(app_key), "W", [a.tenant])
        if r.status_code >= 300:
            print(f"    enrollment failed: {r.status_code} {r.text}")
            return 1
        print(f"    enrolled; app key saved to {app_key_path} (keep it private)")

    app = EnkiClient(a.url, a.app_id, app_key, a.tenant)

    step(3, f"Send an event of type '{a.event_type}' as the app")
    now = datetime.now(timezone.utc).isoformat()
    event = {
        "event_id": f"evt-{uuid.uuid4()}",
        "event_type": a.event_type,
        "timestamp": now,
        "severity": "info",
        "scope": "local",
        "actor_id": a.app_id,
        # Point at things by your system's internal ID. Never a name, date of birth, address,
        # phone, email or record number: Enki keeps these events forever.
        "target_id": str(uuid.uuid4()),
        "target_type": "record",
        "metadata": {"fields_accessed": ["status"]},
    }
    r = app.send_events([event])
    if r.status_code >= 300:
        print(f"    rejected: {r.status_code} {r.text}")
        return 1
    receipt = r.json()
    print(f"    outcome {receipt.get('outcome')}, accepted {receipt.get('accepted_count')}, receipt {receipt.get('txid')}")
    if receipt.get("rejected_items"):
        print(f"    rejected items: {receipt['rejected_items']}")

    step(4, "Read it back as the admin")
    r = admin.audit_events(limit=5)
    print(f"    latest events: {[e['event_type'] for e in r.json().get('events', [])]}")
    r = admin.receipt(receipt["txid"])
    print(f"    receipt chain hash: {r.json().get('chain_hash', '')[:16]}...")
    r = admin.verify_chain()
    v = r.json()
    print(f"    chain valid: {v.get('valid')} ({v.get('verified_count')} receipts checked)")
    print("\nDone. Your app can now send events with its own key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
