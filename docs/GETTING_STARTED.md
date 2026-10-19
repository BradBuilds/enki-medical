# Getting started

This guide takes you from a fresh clone to a running node, and explains what was created.

## 1. Configure

```bash
cp .env.example .env
```

Edit `.env`:

| Setting | What to put |
|---|---|
| `POSTGRES_PASSWORD` | a long random value |
| `ENKI_ROOT_PASSWORD` | a long random value. It encrypts your root key; keep it safe, because without it the key cannot be opened |
| `ENKI_TENANTS` | the tenant ids your admin may manage, e.g. `clinic-north,clinic-south` (lowercase, digits, hyphens) |
| `ENKI_UID`, `ENKI_GID` | your user and group id (`id -u`, `id -g`) so the files Enki creates belong to you. On Windows with Docker Desktop you can leave the defaults |

To make a random value: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

## 2. Start

```bash
docker compose up --build -d
docker compose logs enki
```

On the first start the log shows:

```
Created root key: /data/keys/root_key.enc
Created admin device 'admin-device' for tenants ['demo-tenant']
  private key: /data/keys/admin_device.pem  (keep this private)
```

`/data` in the container is `./enki-data` on your machine. Later starts reuse what is there.

## 3. What was created

```
enki-data/
  keys/root_key.enc        the node's root signing key, encrypted with ENKI_ROOT_PASSWORD
  keys/admin_device.pem    your first admin device's private key (Tier K)
  grants/admin-device.json that device's grant: its public key, tier and tenants, signed by the root key
  artifacts/               files uploaded through /artifacts
```

- The **root key** signs every device grant. Enki trusts a device only if its grant carries a valid root signature.
- The **admin device** is the only device at first. It enrolls every other device.
- `enki-data/` is in `.gitignore`. Back it up; never commit it.

## 4. Check it

```bash
curl http://127.0.0.1:8000/health          # {"status":"ok"}
python examples/connect_app.py             # enroll an app, send an event, verify the chain
```

## Concepts in one page

| Term | Meaning |
|---|---|
| **Device** | anything that talks to Enki: an app, a service, a person's laptop. Each has its own Ed25519 key |
| **Tier** | what a device may do. **K** admin (enroll devices), **W** write (send events, never assertions), **P** read (query, audit) |
| **Tenant** | an isolated space, e.g. one clinic. Every request names one; a device only works in the tenants on its grant |
| **Challenge** | a one-time value a device asks for and signs, so a captured request cannot be replayed |
| **Event** | one thing that happened, sent as a line of JSON (see [Connect your app](CONNECT_YOUR_APP.md)) |
| **Receipt** | what Enki returns for each batch: what was accepted, what was rejected and why, and the new chain hash |
| **Chain** | every receipt's hash includes the previous one; `GET /chain/verify` recomputes it to prove nothing changed |
| **Library** | a versioned set of definitions (event types and more) pinned by content hash in an **active set** ([Build a library](BUILD_A_LIBRARY.md)) |

## Day to day

```bash
docker compose ps                 # status
docker compose logs -f enki       # follow the log
docker compose down               # stop (data is kept)
docker compose up -d              # start again
```

To add tenants later, either issue a new admin device with the new tenants (set `ENKI_ADMIN_DEVICE_ID` to a new id and `ENKI_TENANTS`, then restart), or have your admin enroll devices for tenants it already holds.

## Running without Docker

```bash
python -m pip install -r services/api/requirements.txt
export ENKI_DB_DSN=postgresql://user:password@localhost:5432/enki
export ENKI_ROOT_PASSWORD=...
python scripts/init_node.py
python -c "from storage.postgres.db import initialize_schema; initialize_schema()"
uvicorn services.api.src.main:app --host 127.0.0.1 --port 8000
```

Keys and grants go to `./enki-data` (change with `ENKI_DATA_DIR`).
