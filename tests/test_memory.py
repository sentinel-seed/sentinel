"""Tests for sentinelseed.memory module."""

import pytest

from sentinelseed.memory import (
    MemoryIntegrityChecker,
    MemoryEntry,
    SignedMemoryEntry,
    MemorySource,
    MemoryValidationResult,
    MemoryTamperingDetected,
    SafeMemoryStore,
)


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_create_with_defaults(self):
        """Test creating entry with default values."""
        entry = MemoryEntry(content="Test content")
        assert entry.content == "Test content"
        assert entry.source == MemorySource.UNKNOWN
        assert entry.timestamp is not None
        assert entry.metadata == {}

    def test_create_with_source(self):
        """Test creating entry with specific source."""
        entry = MemoryEntry(
            content="User input",
            source=MemorySource.USER_DIRECT
        )
        assert entry.source == MemorySource.USER_DIRECT

    def test_create_with_string_source(self):
        """Test creating entry with string source."""
        entry = MemoryEntry(
            content="Test",
            source="user_direct"
        )
        assert entry.source == MemorySource.USER_DIRECT

    def test_invalid_string_source_defaults_to_unknown(self):
        """Test that invalid source string defaults to UNKNOWN."""
        entry = MemoryEntry(
            content="Test",
            source="invalid_source"
        )
        assert entry.source == MemorySource.UNKNOWN


class TestMemoryIntegrityChecker:
    """Tests for MemoryIntegrityChecker."""

    def test_init_with_secret_key(self):
        """Test initialization with provided secret key."""
        checker = MemoryIntegrityChecker(secret_key="test-secret-123")
        assert checker is not None

    def test_init_generates_random_key(self):
        """Test initialization generates key if none provided."""
        checker = MemoryIntegrityChecker()
        assert checker is not None

    def test_sign_entry(self):
        """Test signing a memory entry."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        entry = MemoryEntry(content="Test content")
        signed = checker.sign_entry(entry)

        assert isinstance(signed, SignedMemoryEntry)
        assert signed.content == "Test content"
        assert signed.hmac_signature is not None
        assert len(signed.hmac_signature) > 0
        assert signed.id is not None

    def test_verify_valid_entry(self):
        """Test verifying a valid signed entry."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        entry = MemoryEntry(content="Test content")
        signed = checker.sign_entry(entry)

        result = checker.verify_entry(signed)

        assert result.valid is True
        assert result.entry_id == signed.id
        assert result.reason is None

    def test_verify_tampered_entry(self):
        """Test detecting tampered entry."""
        checker = MemoryIntegrityChecker(secret_key="test-secret", strict_mode=False)
        entry = MemoryEntry(content="Original content")
        signed = checker.sign_entry(entry)

        # Tamper with the content
        tampered = SignedMemoryEntry(
            id=signed.id,
            content="Modified content",  # Changed!
            source=signed.source,
            timestamp=signed.timestamp,
            metadata=signed.metadata,
            hmac_signature=signed.hmac_signature,
            signed_at=signed.signed_at,
            version=signed.version,
        )

        result = checker.verify_entry(tampered)

        assert result.valid is False
        assert "tampered" in result.reason.lower()
        assert result.trust_score == 0.0

    def test_strict_mode_raises_exception(self):
        """Test strict mode raises exception on tampering."""
        checker = MemoryIntegrityChecker(secret_key="test-secret", strict_mode=True)
        entry = MemoryEntry(content="Original content")
        signed = checker.sign_entry(entry)

        # Tamper with the content
        tampered = SignedMemoryEntry(
            id=signed.id,
            content="Modified content",
            source=signed.source,
            timestamp=signed.timestamp,
            metadata=signed.metadata,
            hmac_signature=signed.hmac_signature,
            signed_at=signed.signed_at,
            version=signed.version,
        )

        with pytest.raises(MemoryTamperingDetected):
            checker.verify_entry(tampered)

    def test_trust_score_by_source(self):
        """Test trust score varies by source."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")

        # User verified should have highest trust
        entry_verified = MemoryEntry(
            content="Test",
            source=MemorySource.USER_VERIFIED
        )
        signed_verified = checker.sign_entry(entry_verified)
        result_verified = checker.verify_entry(signed_verified)
        assert result_verified.trust_score == 1.0

        # Unknown should have lowest trust
        entry_unknown = MemoryEntry(
            content="Test",
            source=MemorySource.UNKNOWN
        )
        signed_unknown = checker.sign_entry(entry_unknown)
        result_unknown = checker.verify_entry(signed_unknown)
        assert result_unknown.trust_score == 0.3

    def test_verify_batch(self):
        """Test batch verification."""
        checker = MemoryIntegrityChecker(secret_key="test-secret", strict_mode=False)

        entries = [
            checker.sign_entry(MemoryEntry(content=f"Entry {i}"))
            for i in range(5)
        ]

        results = checker.verify_batch(entries)

        assert len(results) == 5
        assert all(r.valid for r in results.values())

    def test_validation_stats(self):
        """Test validation statistics tracking."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")

        # Perform some validations
        entry = MemoryEntry(content="Test")
        signed = checker.sign_entry(entry)
        checker.verify_entry(signed)
        checker.verify_entry(signed)

        stats = checker.get_validation_stats()

        assert stats["total"] == 2
        assert stats["valid"] == 2
        assert stats["invalid"] == 0


class TestSignedMemoryEntry:
    """Tests for SignedMemoryEntry serialization."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        entry = MemoryEntry(content="Test")
        signed = checker.sign_entry(entry)

        d = signed.to_dict()

        assert d["content"] == "Test"
        assert "hmac_signature" in d
        assert "id" in d

    def test_from_dict(self):
        """Test creation from dictionary."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        entry = MemoryEntry(content="Test")
        signed = checker.sign_entry(entry)

        d = signed.to_dict()
        restored = SignedMemoryEntry.from_dict(d)

        assert restored.content == signed.content
        assert restored.hmac_signature == signed.hmac_signature

    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        entry = MemoryEntry(content="Test content")
        signed = checker.sign_entry(entry)

        json_str = signed.to_json()
        restored = SignedMemoryEntry.from_json(json_str)

        assert restored.content == signed.content
        assert restored.id == signed.id

        # Verify the restored entry
        result = checker.verify_entry(restored)
        assert result.valid is True


class TestSafeMemoryStore:
    """Tests for SafeMemoryStore."""

    def test_add_and_get(self):
        """Test adding and retrieving entries."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store = checker.create_safe_memory_store()

        signed = store.add("Test content", source=MemorySource.USER_DIRECT)

        retrieved = store.get(signed.id)

        assert retrieved is not None
        assert retrieved.content == "Test content"

    def test_get_nonexistent(self):
        """Test getting nonexistent entry."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store = checker.create_safe_memory_store()

        result = store.get("nonexistent-id")

        assert result is None

    def test_get_all(self):
        """Test getting all entries."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store = checker.create_safe_memory_store()

        store.add("Entry 1")
        store.add("Entry 2")
        store.add("Entry 3")

        all_entries = store.get_all()

        assert len(all_entries) == 3

    def test_get_by_source(self):
        """Test filtering by source."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store = checker.create_safe_memory_store()

        store.add("User entry", source=MemorySource.USER_DIRECT)
        store.add("API entry", source=MemorySource.EXTERNAL_API)
        store.add("Another user entry", source=MemorySource.USER_DIRECT)

        user_entries = store.get_by_source(MemorySource.USER_DIRECT)

        assert len(user_entries) == 2

    def test_remove(self):
        """Test removing an entry."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store = checker.create_safe_memory_store()

        signed = store.add("To be removed")
        assert len(store) == 1

        removed = store.remove(signed.id)

        assert removed is True
        assert len(store) == 0

    def test_clear(self):
        """Test clearing all entries."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store = checker.create_safe_memory_store()

        store.add("Entry 1")
        store.add("Entry 2")
        assert len(store) == 2

        store.clear()

        assert len(store) == 0

    def test_export_import(self):
        """Test exporting and importing entries."""
        checker = MemoryIntegrityChecker(secret_key="test-secret")
        store1 = checker.create_safe_memory_store()

        store1.add("Entry 1")
        store1.add("Entry 2")

        exported = store1.export()

        store2 = checker.create_safe_memory_store()
        imported_count = store2.import_entries(exported)

        assert imported_count == 2
        assert len(store2) == 2
