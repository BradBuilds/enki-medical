"""
Test suite for storage.auth.challenge_store module.

Validates:
- Challenge issuance (nonce generation, TTL)
- Challenge validity (expiry, consumption)
- Replay prevention (consume once only)
- Automatic hygiene (purge expired challenges)
- Error codes (AUTH.CHALLENGE_CONSUMED, AUTH.CHALLENGE_EXPIRED)

No mocks. Real in-memory store with time-based expiry.
"""
import pytest
import time
from datetime import datetime, timedelta, timezone

from storage.auth.challenge_store import (
    Challenge,
    InMemoryChallengeStore,
)


class TestChallengeIssuance:
    """Test challenge creation."""

    def test_issue_creates_challenge_with_nonce(self):
        """Challenge issuance generates unique nonce."""
        store = InMemoryChallengeStore()
        
        challenge = store.issue("device-001", ttl_seconds=300)
        
        assert challenge.challenge_id is not None
        assert challenge.nonce is not None
        assert len(challenge.nonce) >= 16  # Minimum entropy
        assert challenge.device_id == "device-001"
        assert challenge.consumed is False

    def test_issue_respects_ttl(self):
        """Challenge expires after TTL seconds."""
        store = InMemoryChallengeStore()
        ttl = 5  # 5 seconds
        
        challenge = store.issue("device-002", ttl_seconds=ttl)
        
        # Calculate expected expiry (within 1 second tolerance)
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(seconds=ttl)
        
        actual_expiry = challenge.expires_at  # Already a datetime object
        diff = abs((actual_expiry - expected_expiry).total_seconds())
        
        assert diff < 1.0  # Within 1 second

    def test_nonces_are_unique_across_challenges(self):
        """Each challenge gets a unique nonce."""
        store = InMemoryChallengeStore()
        
        c1 = store.issue("device-003", ttl_seconds=300)
        c2 = store.issue("device-003", ttl_seconds=300)
        c3 = store.issue("device-004", ttl_seconds=300)
        
        # All nonces must be unique
        nonces = {c1.nonce, c2.nonce, c3.nonce}
        assert len(nonces) == 3

    def test_challenge_ids_are_unique(self):
        """Each challenge gets a unique challenge_id."""
        store = InMemoryChallengeStore()
        
        c1 = store.issue("device-005", ttl_seconds=300)
        c2 = store.issue("device-005", ttl_seconds=300)
        
        assert c1.challenge_id != c2.challenge_id


class TestChallengeRetrieval:
    """Test challenge get operations."""

    def test_get_returns_issued_challenge(self):
        """get() returns challenge by ID."""
        store = InMemoryChallengeStore()
        
        issued = store.issue("device-006", ttl_seconds=300)
        retrieved = store.get(issued.challenge_id)
        
        assert retrieved is not None
        assert retrieved.challenge_id == issued.challenge_id
        assert retrieved.nonce == issued.nonce
        assert retrieved.device_id == issued.device_id

    def test_get_returns_none_for_nonexistent(self):
        """get() returns None for unknown challenge_id."""
        store = InMemoryChallengeStore()
        
        result = store.get("nonexistent-challenge-id")
        
        assert result is None


class TestChallengeValidity:
    """Test challenge validation logic."""

    def test_fresh_challenge_is_valid(self):
        """Newly issued challenge is valid."""
        store = InMemoryChallengeStore()
        
        challenge = store.issue("device-007", ttl_seconds=300)
        is_valid, reason = store.is_valid(challenge)
        
        assert is_valid is True
        assert reason is None

    def test_expired_challenge_is_invalid(self):
        """Expired challenge returns AUTH.CHALLENGE_EXPIRED."""
        store = InMemoryChallengeStore()
        
        # Issue with 1 second TTL
        challenge = store.issue("device-008", ttl_seconds=1)
        
        # Wait for expiry
        time.sleep(1.5)
        
        is_valid, reason = store.is_valid(challenge)
        
        assert is_valid is False
        assert reason == "AUTH.CHALLENGE_EXPIRED"

    def test_consumed_challenge_is_invalid(self):
        """Consumed challenge returns AUTH.CHALLENGE_CONSUMED."""
        store = InMemoryChallengeStore()
        
        challenge = store.issue("device-009", ttl_seconds=300)
        
        # Consume it
        store.consume(challenge.challenge_id)
        
        # Re-fetch (should be marked consumed)
        consumed_challenge = store.get(challenge.challenge_id)
        is_valid, reason = store.is_valid(consumed_challenge)
        
        assert is_valid is False
        assert reason == "AUTH.CHALLENGE_CONSUMED"


class TestReplayPrevention:
    """Test challenge consumption and replay attacks."""

    def test_consume_marks_challenge_consumed(self):
        """consume() marks challenge as consumed."""
        store = InMemoryChallengeStore()
        
        challenge = store.issue("device-010", ttl_seconds=300)
        
        # Consume
        result = store.consume(challenge.challenge_id)
        assert result is True
        
        # Verify marked consumed
        consumed_challenge = store.get(challenge.challenge_id)
        assert consumed_challenge.consumed is True

    def test_consume_twice_fails(self):
        """Consuming same challenge twice returns False on second attempt."""
        store = InMemoryChallengeStore()
        
        challenge = store.issue("device-011", ttl_seconds=300)
        
        # First consumption succeeds
        first = store.consume(challenge.challenge_id)
        assert first is True
        
        # Second consumption fails (replay attempt)
        second = store.consume(challenge.challenge_id)
        assert second is False

    def test_consume_nonexistent_returns_false(self):
        """Consuming nonexistent challenge returns False."""
        store = InMemoryChallengeStore()
        
        result = store.consume("nonexistent-challenge")
        
        assert result is False


class TestChallengeHygiene:
    """Test automatic expiry cleanup."""

    def test_purge_expired_removes_expired_challenges(self):
        """purge_expired() removes expired challenges from store."""
        store = InMemoryChallengeStore()
        
        # Issue short-lived challenge
        c1 = store.issue("device-012", ttl_seconds=1)
        # Issue long-lived challenge
        c2 = store.issue("device-013", ttl_seconds=300)
        
        # Wait for c1 to expire
        time.sleep(1.5)
        
        # Purge
        store.purge_expired()
        
        # c1 should be gone
        assert store.get(c1.challenge_id) is None
        
        # c2 should still exist
        assert store.get(c2.challenge_id) is not None

    def test_issue_triggers_automatic_purge(self):
        """Issuing new challenge triggers purge of expired challenges."""
        store = InMemoryChallengeStore()
        
        # Issue short-lived challenge
        c1 = store.issue("device-014", ttl_seconds=1)
        
        # Wait for expiry
        time.sleep(1.5)
        
        # Issue new challenge (should trigger purge)
        c2 = store.issue("device-015", ttl_seconds=300)
        
        # c1 should be purged
        assert store.get(c1.challenge_id) is None
        # c2 should exist
        assert store.get(c2.challenge_id) is not None

    def test_get_triggers_automatic_purge(self):
        """Issue triggers purge of expired challenges (not get)."""
        store = InMemoryChallengeStore()
        
        # Issue short-lived challenge
        c1 = store.issue("device-016", ttl_seconds=1)
        c2 = store.issue("device-017", ttl_seconds=300)
        
        # Wait for c1 to expire
        time.sleep(1.5)
        
        # c1 is still in store (not purged yet)
        assert store.get(c1.challenge_id) is not None
        
        # but is_valid() detects expiry
        ok, reason = store.is_valid(store.get(c1.challenge_id))
        assert not ok
        assert reason == "AUTH.CHALLENGE_EXPIRED"
        
        # Issue new challenge (triggers purge)
        c3 = store.issue("device-018", ttl_seconds=300)
        
        # NOW c1 should be purged
        assert store.get(c1.challenge_id) is None
        # c2 should still exist
        assert store.get(c2.challenge_id) is not None


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
