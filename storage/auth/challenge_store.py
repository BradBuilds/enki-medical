# storage/auth/challenge_store.py
"""
Challenge store (in-memory).

- Replay prevention: single-use challenges (consumed flag).
- Hygiene: opportunistic purge of expired challenges.
- Production can swap to Redis behind same interface.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class Challenge:
    challenge_id: str
    device_id: str
    nonce: str              # base64(32 bytes)
    issued_at: datetime
    expires_at: datetime
    consumed: bool = False


class InMemoryChallengeStore:
    def __init__(self):
        self._store: dict[str, Challenge] = {}

    def purge_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired_ids = [cid for cid, c in self._store.items() if now > c.expires_at]
        for cid in expired_ids:
            self._store.pop(cid, None)

    def issue(self, device_id: str, ttl_seconds: int) -> Challenge:
        self.purge_expired()

        challenge_id = str(uuid.uuid4())
        nonce = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=ttl_seconds)

        c = Challenge(
            challenge_id=challenge_id,
            device_id=device_id,
            nonce=nonce,
            issued_at=issued_at,
            expires_at=expires_at,
            consumed=False,
        )
        self._store[challenge_id] = c
        return c

    def get(self, challenge_id: str) -> Optional[Challenge]:
        # Return challenge if it exists, even if expired
        # This allows is_valid() to detect expiry and return proper error code
        # Purge happens during issue() to keep store size bounded
        return self._store.get(challenge_id)

    def consume(self, challenge_id: str) -> bool:
        c = self._store.get(challenge_id)
        if not c:
            return False
        if c.consumed:
            return False
        c.consumed = True
        return True

    def is_valid(self, c: Challenge) -> tuple[bool, str | None]:
        now = datetime.now(timezone.utc)
        if c.consumed:
            return False, "AUTH.CHALLENGE_CONSUMED"
        if now > c.expires_at:
            return False, "AUTH.CHALLENGE_EXPIRED"
        return True, None
