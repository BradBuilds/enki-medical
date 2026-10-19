# Connect your app

Your app becomes a **device**: it has its own key, your admin enrolls it, and every request it makes is signed. The fastest way in is to copy [`examples/enki_client.py`](../examples/enki_client.py) into your project; [`examples/connect_app.py`](../examples/connect_app.py) shows the whole flow running.

## 1. Give the app a key

```python
from enki_client import new_key, public_key_b64
app_key = new_key("secrets/my-app.pem")        # keep this file private; it is the app's identity
print(public_key_b64(app_key))                 # the public half, for enrollment
```

## 2. Enroll it (done once, by your admin)

```python
from enki_client import EnkiClient, load_key
admin = EnkiClient("http://127.0.0.1:8000", "admin-device", load_key("enki-data/keys/admin_device.pem"), "demo-tenant")
r = admin.enroll_device("my-app", public_key_b64(app_key), tier="W", tenant_scopes=["demo-tenant"])
print(r.status_code, r.json())
```

Pick the tier the app needs and nothing more:

| Tier | Can | Typical use |
|---|---|---|
| W | send events (not assertions) | an app or integration that reports what happened |
| P | read: audit events, receipts, chain, queries | a dashboard or compliance report |
| K | enroll and manage devices, everything else | administrators only |

## 3. Send events

```python
app = EnkiClient("http://127.0.0.1:8000", "my-app", app_key, "demo-tenant")
r = app.send_events([{
    "event_id": "evt-5b1e2c4e-0f7a-4f0e-9c1d-2a6b8e3f9d10",   # unique, lowercase
    "event_type": "node.heartbeat",                           # built-in, or from your library
    "timestamp": "2026-10-18T14:00:00Z",
    "severity": "info",                                       # info | warning | error | critical
    "scope": "local",                                         # local | shared | global
    "actor_id": "my-app",
    "target_id": "7f3a9c2e-1d4b-4e8a-b6f0-0c5d2e9a8b71",      # your internal id, never a name
    "target_type": "record",
    "metadata": {"fields_accessed": ["status"]}
}])
receipt = r.json()
```

Events are sent as JSON lines (`application/x-ndjson`), so one request can carry many. The receipt tells you exactly what happened:

```json
{
  "outcome": "FULL_ACCEPT",
  "accepted_count": 1,
  "rejected_count": 0,
  "txid": "3",
  "chain_hash": "ca034d09…",
  "rejected_items": []
}
```

`outcome` is `FULL_ACCEPT`, `PARTIAL_ACCEPT` or `FULL_REJECT`; each rejected line says why (bad JSON, missing field, or an event type no admitted library declares).

**Only send IDs.** Read [Privacy](PRIVACY.md) before you design your events.

## 4. Read and verify

With a P or K device:

```python
reader.audit_events(limit=20)     # newest events for the tenant
reader.receipt("3")               # one receipt by txid
reader.verify_chain()             # {"valid": true, "verified_count": …}
```

## How signing works (if you are not using Python)

For every request except `GET /health` and `GET /admin/challenges/issue`:

1. `GET /admin/challenges/issue?device_id=<id>` returns `challenge_id`, `nonce`, `issued_at`, `expires_at`.
2. Compute `body_sha256` = lowercase hex SHA-256 of the exact request body (empty string for GET).
3. Build this object and serialise it as canonical JSON: keys sorted, no spaces, UTF-8:

   ```json
   {"body_sha256":"…","challenge_id":"…","device_id":"…","expires_at":"…","issued_at":"…","method":"POST","nonce":"…","path":"/ingest/events","tenant_id":"…"}
   ```

   `path` includes the query string if there is one (e.g. `/audit-events?limit=20`).
4. Sign those bytes with the device's Ed25519 private key; base64-encode the signature.
5. Send headers `X-Device-ID`, `X-Challenge-ID`, `X-Tenant-ID`, `X-Body-SHA256`, `X-Signature`.

Each challenge works once and expires (default 5 minutes). The full contract is in [contracts/CANONICAL_ENVELOPE_SPEC.md](../contracts/CANONICAL_ENVELOPE_SPEC.md).

## Common errors

| Error code | Usual cause |
|---|---|
| `AUTH.SIGNATURE_INVALID` | envelope fields or key do not match; check `path` includes the query string and the body hash is of the exact bytes sent |
| `AUTH.CHALLENGE_CONSUMED`, `AUTH.CHALLENGE_EXPIRED` | challenge already used or expired; get a fresh one per request |
| `TENANT.SCOPE_FORBIDDEN` | the device's grant does not include that tenant |
| `AUTH.ADMIN_TIER_REQUIRED` | only Tier K devices can enroll devices |
| `AUTH.DEVICE_NOT_ENROLLED`, `AUTH.GRANT_EXPIRED` | the device was never enrolled, or its grant ran out (default 365 days); enroll it again |
| `CONNECTOR.EVENT_NOT_ALLOWED` | a Tier W device tried to send an `assertion.*` event, or a type outside its allowlist |

All codes are listed in [services/api/API_ERROR_CODES.md](../services/api/API_ERROR_CODES.md).
