# Enki Medical

**An open-source, tamper-evident record of what happened to your health data: who sent what, who read what, and proof that nothing was changed afterwards.**

Enki Medical is a small service you run next to your own app. Your app sends it events ("record 7f3a… was viewed by service X"), and Enki stores them in an append-only, hash-chained log that anyone with access can verify. You decide what kinds of events exist by writing your own **libraries**, and you connect your apps as signed **devices**.

It is a governance core, not a medical app: it does not store patient records, and it should never receive names or other identifiers (see [Privacy](docs/PRIVACY.md)).

## What you get

- **Append-only, tamper-evident log.** Every batch of events gets a receipt whose hash chains to the previous one. `GET /chain/verify` proves the chain is unbroken.
- **Signed devices, per request.** Every app or person that talks to Enki is a device with its own Ed25519 key. Each request is signed against a one-time challenge.
- **Three tiers.** K (admin: enrolls devices), W (write: sends events), P (read: queries and audits).
- **Tenant isolation.** Every request is scoped to a tenant; a device only sees the tenants it was granted.
- **Your own vocabulary.** Event types come from versioned libraries that are pinned by content hash. A library that changes after it was admitted is refused.

## Quick start (about 5 minutes)

You need Docker and Python 3.10+ (for the examples).

```bash
git clone https://github.com/BradBuilds/enki-medical.git
cd enki-medical
cp .env.example .env          # then set POSTGRES_PASSWORD and ENKI_ROOT_PASSWORD to long random values
docker compose up --build -d  # first start creates your root key and admin device in ./enki-data
```

Check it is running:

```bash
curl http://127.0.0.1:8000/health
```

Connect an example app, send an event, read it back and verify the chain:

```bash
python -m pip install httpx cryptography
python examples/connect_app.py
```

You should see the app enrolled, the event accepted with a receipt, and `chain valid: True`.

## Next steps

| I want to… | Read |
|---|---|
| understand what was just created and how to run it day to day | [Getting started](docs/GETTING_STARTED.md) |
| connect my own app | [Connect your app](docs/CONNECT_YOUR_APP.md) |
| define my own event types | [Build a library](docs/BUILD_A_LIBRARY.md) |
| keep identifiers out of the log | [Privacy](docs/PRIVACY.md) |
| see every endpoint and error code | [API contract](contracts/CONTRACT_INDEX.md) and [error codes](services/api/API_ERROR_CODES.md) |
| read the design specifications | [docs/reference](docs/reference/) |

## Run the tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest            # database tests are skipped without a database
```

With a throwaway database for the full suite:

```bash
docker run -d --name enki-test-db -e POSTGRES_USER=enki -e POSTGRES_PASSWORD=test -e POSTGRES_DB=enki -p 127.0.0.1:55432:5432 postgres:16
ENKI_DB_DSN=postgresql://enki:test@127.0.0.1:55432/enki python -m pytest
docker rm -f enki-test-db
```

The tests create a throwaway root key and admin device for each run; no keys are stored in this repository.

## Repository layout

```
services/api/   the HTTP API (FastAPI)
storage/        auth, signing, ingest, hash chain, PostgreSQL schema
core/           validation, libraries (packs), governance spine
libraries/      the built-in vocabulary libraries; add yours here
schemas/        JSON schemas for events, packs and active sets
contracts/      the locked API contract and golden request/response examples
scripts/        init_node.py (first run), library.py (make your own library)
examples/       enki_client.py (a client to copy) and connect_app.py (end to end)
cmd/, internal/ the gdu command-line tool (Go): pack and active-set utilities
```

## Licence

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Libraries you write are yours to license as you choose.
