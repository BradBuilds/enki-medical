"""
ENKI Phase 4 API

Minimal API layer integrating Phase 3.6 device authentication.

Author: ENKI System
Version: 0.1.0 (Phase 4 skeleton)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from storage.auth.config import GRANTS_DIR, ROOT_KEY_PATH, ROOT_KEY_PASSWORD
from storage.auth.root_key import load_root_key
from storage.auth.grant_store import GrantStore
from storage.auth.challenge_store import InMemoryChallengeStore

from services.api.src.routes.health import router as health_router
from services.api.src.routes.admin import router as admin_router
from services.api.src.routes.ingest import router as ingest_router
from services.api.src.routes.query import router as query_router
from services.api.src.routes.receipts import router as receipts_router
from services.api.src.routes.audit import router as audit_router
from services.api.src.routes.chain import router as chain_router
from services.api.src.routes.artifacts import router as artifacts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager (replaces deprecated @app.on_event("startup")).
    
    Startup (before yield):
    - Validate ROOT_KEY_PASSWORD environment variable
    - Initialize grant_store (Phase 3.6 device grants)
    - Initialize challenge_store (in-memory challenge tracking)
    - Load root_key for device grant signature verification
    - Extract root_public_key_raw for Ed25519 verification
    - Assign all singletons to app.state
    
    Shutdown (after yield):
    - Optional cleanup (none needed currently)
    """
    # --- Phase 3.6 Singletons ---
    if not ROOT_KEY_PASSWORD:
        raise RuntimeError(
            "ROOT_KEY_PASSWORD is not set. Ensure ENKI_ROOT_KEY_PASSWORD_ENV points "
            "to a valid env var (e.g., ENKI_ROOT_PASSWORD) and that it is set."
        )

    grant_store = GrantStore(GRANTS_DIR)
    challenge_store = InMemoryChallengeStore()

    root_key = load_root_key(ROOT_KEY_PATH, ROOT_KEY_PASSWORD)
    # Root public key must be raw bytes for Ed25519 verification
    root_public_key_raw = root_key.public_key_bytes_raw()

    app.state.grant_store = grant_store
    app.state.challenge_store = challenge_store
    app.state.root_key = root_key
    app.state.root_public_key_raw = root_public_key_raw
    
    yield
    
    # Optional shutdown logic (none needed currently)


def create_app() -> FastAPI:
    app = FastAPI(title="ENKI Phase 4 API", version="0.1.0", lifespan=lifespan)

    # Exception handler: Convert missing auth headers (422) to ENKI 401 envelope
    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        Convert missing-auth-header validation errors into ENKI 401 envelope.
        Keep other validation errors as FastAPI default 422.
        
        Contract Lock v1.0.0: Ensures missing auth headers return proper
        API.UNAUTHORIZED envelope instead of framework-default 422.
        """
        errors = exc.errors()
        
        # Detect missing required auth headers
        # Pydantic error: {'loc': ('header', 'x-device-id'), 'msg': 'Field required', 'type': 'missing'}
        missing_headers = set()
        for e in errors:
            loc = e.get("loc") or ()
            if (
                len(loc) >= 2 
                and loc[0] == "header" 
                and e.get("type") in ("missing", "value_error.missing")
            ):
                missing_headers.add(str(loc[1]).lower())
        
        # Required auth headers (x-body-sha256 is conditional, excluded)
        required_auth_headers = {
            "x-device-id",
            "x-challenge-id",
            "x-tenant-id",
            "x-signature",
        }
        
        # If any required auth header is missing, return ENKI 401
        if missing_headers & required_auth_headers:
            return JSONResponse(
                status_code=401,
                content={
                    "error_code": "API.UNAUTHORIZED",
                    "detail": "Authentication required",
                    "meta": {
                        "missing_headers": sorted(list(missing_headers & required_auth_headers))
                    },
                },
            )
        
        # Otherwise: preserve FastAPI 422 for real validation issues
        return JSONResponse(status_code=422, content={"detail": errors})

    # Routers (order is not functionally critical, but keeps docs tidy)
    app.include_router(health_router)
    app.include_router(admin_router)
    app.include_router(ingest_router)
    app.include_router(query_router)
    app.include_router(receipts_router)
    app.include_router(audit_router)
    app.include_router(chain_router)
    app.include_router(artifacts_router)

    return app


app = create_app()
