"""
Tests for Memory Integration in Letta MemoryGuardTool.

These tests verify that the MemoryGuardTool correctly uses the core
MemoryIntegrityChecker for HMAC-based memory verification.

Run with: python -m pytest src/sentinelseed/integrations/letta/test_memory_integration.py -v
"""

import pytest

# Check if memory module is available
try:
    from sentinelseed.memory import (
        MemoryIntegrityChecker,
        MemorySource,
    )
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestMemoryGuardToolInitialization:
    """Tests for MemoryGuardTool initialization."""

    def test_initialize_with_valid_secret(self):
        """Tool should initialize with valid secret."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("my-secret-key")

        assert tool._checker is not None
        assert tool._store is not None
        stats = tool.get_stats()
        assert stats["enabled"] is True

    def test_initialize_with_none_raises(self):
        """Tool should raise ValueError for None secret."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        with pytest.raises(ValueError, match="cannot be None"):
            tool.initialize(None)

    def test_initialize_with_empty_raises(self):
        """Tool should raise ValueError for empty secret."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        with pytest.raises(ValueError, match="cannot be empty"):
            tool.initialize("")

    def test_run_without_initialization_returns_error(self):
        """Running without initialization should return error."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        result = tool.run(memory_label="test", content="test content")

        assert "ERROR" in result
        assert "not initialized" in result


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestMemoryGuardToolRegistration:
    """Tests for memory registration."""

    def test_register_memory_returns_hash(self):
        """Registering memory should return HMAC hash."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        result = tool.run(memory_label="human", content="User info")

        assert result.startswith("HASH:")
        hash_value = result.split(": ")[1]
        assert len(hash_value) == 64  # SHA256 hex

    def test_register_multiple_memories(self):
        """Should be able to register multiple memory blocks."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        result1 = tool.run(memory_label="human", content="User info")
        result2 = tool.run(memory_label="persona", content="AI assistant")
        result3 = tool.run(memory_label="system", content="System config")

        assert "HASH:" in result1
        assert "HASH:" in result2
        assert "HASH:" in result3

        stats = tool.get_stats()
        assert stats["registered_blocks"] == 3
        assert "human" in stats["labels"]
        assert "persona" in stats["labels"]
        assert "system" in stats["labels"]

    def test_get_hash_of_registered_memory(self):
        """Should be able to get hash of registered memory."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        # Register
        result1 = tool.run(memory_label="human", content="User info")
        hash1 = result1.split(": ")[1]

        # Get hash without content
        result2 = tool.run(memory_label="human")

        assert "HASH:" in result2
        hash2 = result2.split(": ")[1]
        assert hash1 == hash2

    def test_get_hash_of_unregistered_returns_error(self):
        """Getting hash of unregistered memory should return error."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        result = tool.run(memory_label="unknown")

        assert "ERROR" in result
        assert "not registered" in result


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestMemoryGuardToolVerification:
    """Tests for memory verification."""

    def test_verify_correct_hash(self):
        """Verification with correct hash should return VERIFIED."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        # Register
        result = tool.run(memory_label="human", content="User info")
        hash_value = result.split(": ")[1]

        # Verify
        result = tool.run(memory_label="human", expected_hash=hash_value)

        assert "VERIFIED" in result

    def test_verify_wrong_hash(self):
        """Verification with wrong hash should return TAMPERED."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        # Register
        tool.run(memory_label="human", content="User info")

        # Verify with wrong hash
        result = tool.run(memory_label="human", expected_hash="wrong-hash")

        assert "TAMPERED" in result

    def test_detect_content_modification(self):
        """Should detect when content has been modified."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        # Register original content
        result = tool.run(memory_label="human", content="Original content")
        original_hash = result.split(": ")[1]

        # Try to verify with modified content
        result = tool.run(
            memory_label="human",
            content="TAMPERED content",
            expected_hash=original_hash
        )

        assert "TAMPERED" in result

    def test_verify_stored_entry_with_expected_hash(self):
        """Should verify stored entry against expected hash."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        # Register
        result = tool.run(memory_label="human", content="User info")
        hash_value = result.split(": ")[1]

        # Verify stored entry (without re-registering content)
        result = tool.run(memory_label="human", expected_hash=hash_value)

        assert "VERIFIED" in result

    def test_re_register_same_content_changes_hash(self):
        """Re-registering content creates new entry with different hash.

        This is expected behavior because the hash includes timestamp and ID.
        Each registration is a new entry.
        """
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret-key")

        # Register same content twice
        result1 = tool.run(memory_label="human", content="User info")
        hash1 = result1.split(": ")[1]

        result2 = tool.run(memory_label="human", content="User info")
        hash2 = result2.split(": ")[1]

        # Hashes should be different (different timestamp/id)
        # This is expected - each registration is a new entry
        assert hash1 != hash2


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestMemoryGuardToolInputValidation:
    """Tests for input validation."""

    def test_none_label_returns_error(self):
        """None label should return error."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret")

        result = tool.run(memory_label=None, content="test")

        assert "ERROR" in result
        assert "cannot be None" in result

    def test_empty_label_returns_error(self):
        """Empty label should return error."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret")

        result = tool.run(memory_label="", content="test")

        assert "ERROR" in result
        assert "cannot be empty" in result

    def test_invalid_label_type_returns_error(self):
        """Non-string label should return error."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret")

        result = tool.run(memory_label=123, content="test")

        assert "ERROR" in result
        assert "must be a string" in result


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestMemoryGuardToolStats:
    """Tests for statistics."""

    def test_stats_disabled_when_not_initialized(self):
        """Stats should show disabled when not initialized."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        stats = tool.get_stats()

        assert stats["enabled"] is False

    def test_stats_track_registered_blocks(self):
        """Stats should track registered blocks."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret")

        tool.run(memory_label="human", content="User")
        tool.run(memory_label="persona", content="AI")

        stats = tool.get_stats()

        assert stats["enabled"] is True
        assert stats["registered_blocks"] == 2
        assert set(stats["labels"]) == {"human", "persona"}


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestMemoryGuardToolClear:
    """Tests for clearing memory."""

    def test_clear_removes_all_memories(self):
        """Clear should remove all registered memories."""
        from sentinelseed.integrations.letta import MemoryGuardTool

        tool = MemoryGuardTool()
        tool.initialize("secret")

        tool.run(memory_label="human", content="User")
        tool.run(memory_label="persona", content="AI")

        stats = tool.get_stats()
        assert stats["registered_blocks"] == 2

        tool.clear()

        stats = tool.get_stats()
        assert stats["registered_blocks"] == 0
        assert stats["labels"] == []


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestCreateMemoryGuardTool:
    """Tests for create_memory_guard_tool function."""

    def test_create_initializes_checker(self):
        """create_memory_guard_tool should initialize checker."""
        from sentinelseed.integrations.letta import create_memory_guard_tool

        tool = create_memory_guard_tool(client=None, secret="my-secret")

        assert tool._checker is not None
        assert tool._store is not None

    def test_create_with_none_secret_raises(self):
        """create_memory_guard_tool should raise for None secret."""
        from sentinelseed.integrations.letta import create_memory_guard_tool

        with pytest.raises(ValueError, match="cannot be None"):
            create_memory_guard_tool(client=None, secret=None)

    def test_create_with_empty_secret_raises(self):
        """create_memory_guard_tool should raise for empty secret."""
        from sentinelseed.integrations.letta import create_memory_guard_tool

        with pytest.raises(ValueError, match="cannot be empty"):
            create_memory_guard_tool(client=None, secret="")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
