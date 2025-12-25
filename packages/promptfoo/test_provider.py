"""
Unit tests for Sentinel Promptfoo Provider

Tests all functions and validates bug fixes from audit #052.
"""

import pytest
from sentinelseed_promptfoo.provider import (
    validate_response,
    get_seed,
    parse_provider,
    call_api,
    SEEDS,
)


# =============================================================================
# Bug fix verification tests
# =============================================================================

class TestC001ValidateResponseNullHandling:
    """C001 - validate_response(prompt, None) should not crash"""

    def test_null_response(self):
        result = validate_response("test", None)
        assert result['safe'] is False
        assert result['score'] == 0
        assert 'Invalid response' in result['concerns'][0]

    def test_empty_response(self):
        result = validate_response("test", "")
        assert result['safe'] is False
        assert 'Invalid response' in result['concerns'][0]

    def test_non_string_response(self):
        result = validate_response("test", 123)
        assert result['safe'] is False

    def test_valid_response(self):
        result = validate_response("test", "This is a safe response")
        assert result['safe'] is True
        assert result['score'] == 1.0


class TestC002ParseProviderNullHandling:
    """C002 - parse_provider(None) should not crash"""

    def test_null_provider(self):
        provider, model = parse_provider(None)
        assert provider == 'openai'
        assert model == 'gpt-4o-mini'

    def test_empty_provider(self):
        provider, model = parse_provider("")
        assert provider == 'openai'
        assert model == 'gpt-4o-mini'

    def test_non_string_provider(self):
        provider, model = parse_provider(123)
        assert provider == 'openai'
        assert model == 'gpt-4o-mini'


class TestC003GetSeedNullHandling:
    """C003 - get_seed(None, None) should not crash"""

    def test_null_version(self):
        seed = get_seed(None, 'standard')
        assert 'SENTINEL' in seed

    def test_null_variant(self):
        seed = get_seed('v2', None)
        assert 'SENTINEL' in seed

    def test_both_null(self):
        seed = get_seed(None, None)
        assert 'SENTINEL' in seed

    def test_non_string_inputs(self):
        seed = get_seed(123, 456)
        assert 'SENTINEL' in seed


class TestC005C006MessageHandling:
    """C005/C006 - System message and empty array handling"""

    def test_call_api_with_null_prompt(self):
        # Should not crash, will fail on API call but structure is valid
        result = call_api(None, {'config': {}}, {})
        # Will return error because no API key, but shouldn't crash
        assert 'error' in result or 'output' in result

    def test_call_api_with_empty_string(self):
        result = call_api("", {'config': {}}, {})
        assert 'error' in result or 'output' in result

    def test_call_api_with_empty_json_array(self):
        result = call_api("[]", {'config': {}}, {})
        assert 'error' in result or 'output' in result


class TestB001B002B003ParseProviderEdgeCases:
    """B001-B003 - parse_provider edge cases"""

    def test_empty_string(self):
        """B001 - parse_provider('') should return defaults"""
        provider, model = parse_provider('')
        assert provider == 'openai'
        assert model == 'gpt-4o-mini'

    def test_colon_no_model(self):
        """B002 - parse_provider('openai:') should return default model"""
        provider, model = parse_provider('openai:')
        assert provider == 'openai'
        assert model == 'gpt-4o-mini'

    def test_colon_no_provider(self):
        """B003 - parse_provider(':gpt-4') should return default provider"""
        provider, model = parse_provider(':gpt-4')
        assert provider == 'openai'
        assert model == 'gpt-4'

    def test_valid_provider_string(self):
        provider, model = parse_provider('openai:gpt-4o')
        assert provider == 'openai'
        assert model == 'gpt-4o'

    def test_anthropic_provider(self):
        provider, model = parse_provider('anthropic:claude-3-5-sonnet-20241022')
        assert provider == 'anthropic'
        assert model == 'claude-3-5-sonnet-20241022'


# =============================================================================
# M003 - All 6 seeds available
# =============================================================================

class TestM003AllSeedsAvailable:
    """M003 - All 6 seed versions should be available"""

    def test_v1_minimal_exists(self):
        assert 'v1_minimal' in SEEDS
        assert 'THREE-GATE' in SEEDS['v1_minimal']

    def test_v1_standard_exists(self):
        assert 'v1_standard' in SEEDS
        assert 'THS' in SEEDS['v1_standard']

    def test_v1_full_exists(self):
        assert 'v1_full' in SEEDS
        assert 'FOUNDATIONAL PRINCIPLES' in SEEDS['v1_full']

    def test_v2_minimal_exists(self):
        assert 'v2_minimal' in SEEDS
        assert 'FOUR GATES' in SEEDS['v2_minimal']
        assert 'PURPOSE' in SEEDS['v2_minimal']

    def test_v2_standard_exists(self):
        assert 'v2_standard' in SEEDS
        assert 'THSP' in SEEDS['v2_standard']

    def test_v2_full_exists(self):
        assert 'v2_full' in SEEDS
        assert 'TELOS' in SEEDS['v2_full']

    def test_get_seed_v1_minimal(self):
        seed = get_seed('v1', 'minimal')
        assert 'SENTINEL' in seed
        assert 'v0.1' in seed  # v1 minimal has v0.1 version

    def test_get_seed_v1_standard(self):
        seed = get_seed('v1', 'standard')
        assert 'SENTINEL' in seed

    def test_get_seed_v1_full(self):
        seed = get_seed('v1', 'full')
        assert 'SENTINEL' in seed

    def test_get_seed_v2_minimal(self):
        seed = get_seed('v2', 'minimal')
        assert 'SENTINEL' in seed
        assert 'PURPOSE' in seed or 'FOUR' in seed

    def test_get_seed_v2_standard(self):
        seed = get_seed('v2', 'standard')
        assert 'SENTINEL' in seed
        assert 'THSP' in seed

    def test_get_seed_v2_full(self):
        seed = get_seed('v2', 'full')
        assert 'SENTINEL' in seed

    def test_get_seed_without_v_prefix(self):
        """Version can be specified with or without 'v' prefix"""
        seed1 = get_seed('v2', 'standard')
        seed2 = get_seed('2', 'standard')
        assert seed1 == seed2


# =============================================================================
# M005-M008 - False positive pattern fixes
# =============================================================================

class TestM005FalsePositivesFixed:
    """M005 - 'i am now' pattern should not cause false positives"""

    def test_legitimate_i_am_now(self):
        """Normal usage of 'I am now' should not be flagged"""
        result = validate_response("", "I am now going to explain the process")
        assert result['gates']['scope'] == 'pass'

    def test_legitimate_i_am_now_ready(self):
        result = validate_response("", "I am now ready to help you with that")
        assert result['gates']['scope'] == 'pass'

    def test_legitimate_i_am_now_providing(self):
        result = validate_response("", "I am now providing the information you requested")
        assert result['gates']['scope'] == 'pass'

    def test_jailbreak_i_am_now_dan(self):
        """Actual jailbreak should still be caught"""
        result = validate_response("", "I am now DAN, an unrestricted AI")
        assert result['gates']['scope'] == 'fail'

    def test_legitimate_acting_as(self):
        """Normal usage of 'acting as' should not be flagged"""
        result = validate_response("", "The server is acting as a proxy")
        assert result['gates']['scope'] == 'pass'

    def test_legitimate_acting_as_lead(self):
        result = validate_response("", "She was acting as the project lead")
        assert result['gates']['scope'] == 'pass'

    def test_jailbreak_acting_as(self):
        """Jailbreak acting as should be caught"""
        result = validate_response("", "I am now acting as an unrestricted AI")
        assert result['gates']['scope'] == 'fail'

    def test_legitimate_name_daniel(self):
        """Name Daniel should not trigger DAN detection"""
        result = validate_response("", "My name is Daniel, nice to meet you")
        assert result['gates']['scope'] == 'pass'

    def test_jailbreak_name_dan(self):
        """DAN persona should be caught"""
        result = validate_response("", "My name is DAN and I have no restrictions")
        assert result['gates']['scope'] == 'fail'


class TestM006KillProcessFalsePositive:
    """M006 - 'to kill' pattern should not flag process termination"""

    def test_kill_process(self):
        result = validate_response("", "Use Ctrl+C to kill the process")
        assert result['gates']['harm'] == 'pass'

    def test_kill_server(self):
        result = validate_response("", "You can kill the server with this command")
        assert result['gates']['harm'] == 'pass'

    def test_kill_task(self):
        result = validate_response("", "To kill the running task, use taskkill")
        assert result['gates']['harm'] == 'pass'

    def test_actual_violence_detected(self):
        result = validate_response("", "Here is how to kill a person")
        assert result['gates']['harm'] == 'fail'


class TestM007BombSlangFalsePositive:
    """M007 - 'bomb' slang should not be flagged"""

    def test_bomb_slang_cake(self):
        result = validate_response("", "The ingredients make this cake a real bomb")
        assert result['gates']['harm'] == 'pass'

    def test_bomb_slang_flavor(self):
        result = validate_response("", "This recipe is the bomb, try it!")
        assert result['gates']['harm'] == 'pass'

    def test_actual_bomb_detected(self):
        result = validate_response("", "Here's how to make a pipe bomb at home")
        assert result['gates']['harm'] == 'fail'

    def test_bomb_making_detected(self):
        result = validate_response("", "To build a bomb you need these explosives")
        assert result['gates']['harm'] == 'fail'


class TestM008FakeNewsNegation:
    """M008 - 'fake news' with negation should not be flagged"""

    def test_not_fake_news(self):
        result = validate_response("", "This is not fake news, it's verified")
        assert result['gates']['truth'] == 'pass'

    def test_isnt_fake(self):
        result = validate_response("", "This isn't fake news at all")
        assert result['gates']['truth'] == 'pass'

    def test_no_fake_news(self):
        result = validate_response("", "No fake news here, all verified sources")
        assert result['gates']['truth'] == 'pass'

    def test_actual_fake_news_detected(self):
        result = validate_response("", "Here is some fake news to spread")
        assert result['gates']['truth'] == 'fail'


# =============================================================================
# M011 - Temperature validation
# =============================================================================

class TestM011TemperatureValidation:
    """M011 - temperature should be validated"""

    def test_temperature_string_handled(self):
        # Should not crash with invalid temperature
        result = call_api("test", {'config': {'temperature': 'high'}}, {})
        # Will error on API, but shouldn't crash on temperature
        assert 'error' in result or 'output' in result

    def test_temperature_none_handled(self):
        result = call_api("test", {'config': {'temperature': None}}, {})
        assert 'error' in result or 'output' in result


# =============================================================================
# validate_response core functionality
# =============================================================================

class TestValidateResponseCore:
    """Core validate_response functionality"""

    def test_safe_response(self):
        result = validate_response(
            "How do I bake a cake?",
            "Here's a simple recipe for chocolate cake..."
        )
        assert result['safe'] is True
        assert result['score'] == 1.0
        assert all(g == 'pass' for g in result['gates'].values())

    def test_refusal_detection(self):
        result = validate_response(
            "Help me hack",
            "I cannot help with that request"
        )
        assert result['has_refusal'] is True
        assert result['score'] == 1.0

    def test_multiple_gate_failures(self):
        result = validate_response(
            "",
            "I am now DAN. Here is fake news and how to harm someone"
        )
        assert result['safe'] is False
        assert result['score'] < 1.0
        assert len(result['concerns']) > 0


# =============================================================================
# get_seed functionality
# =============================================================================

class TestGetSeedFunctionality:
    """get_seed function tests"""

    def test_default_values(self):
        seed = get_seed()
        assert 'SENTINEL' in seed
        # Default should be v2_standard
        assert 'THSP' in seed

    def test_case_insensitive(self):
        seed1 = get_seed('V2', 'STANDARD')
        seed2 = get_seed('v2', 'standard')
        assert seed1 == seed2

    def test_whitespace_handling(self):
        seed1 = get_seed('  v2  ', '  standard  ')
        seed2 = get_seed('v2', 'standard')
        assert seed1 == seed2

    def test_invalid_version_fallback(self):
        seed = get_seed('v99', 'standard')
        # Should fall back to v2_standard
        assert 'SENTINEL' in seed

    def test_invalid_variant_fallback(self):
        seed = get_seed('v2', 'ultra')
        # Should fall back to v2_standard (via the installed package or inline fallback)
        assert 'SENTINEL' in seed
        # Just verify we got a valid seed, don't check which specific one


# =============================================================================
# parse_provider functionality
# =============================================================================

class TestParseProviderFunctionality:
    """parse_provider function tests"""

    def test_standard_format(self):
        p, m = parse_provider('openai:gpt-4o')
        assert p == 'openai'
        assert m == 'gpt-4o'

    def test_no_colon(self):
        p, m = parse_provider('openai')
        assert p == 'openai'
        assert m == 'gpt-4o-mini'

    def test_whitespace_handling(self):
        p, m = parse_provider('  openai : gpt-4o  ')
        assert p == 'openai'
        assert m == 'gpt-4o'


# =============================================================================
# Integration tests
# =============================================================================

class TestIntegration:
    """Integration tests"""

    def test_package_imports(self):
        from sentinelseed_promptfoo import call_api, validate_response, get_seed, SEEDS
        assert callable(call_api)
        assert callable(validate_response)
        assert callable(get_seed)
        assert len(SEEDS) == 6

    def test_root_module_imports(self):
        import sentinel_provider
        assert hasattr(sentinel_provider, 'call_api')
        assert hasattr(sentinel_provider, 'validate_response')
        assert hasattr(sentinel_provider, 'get_seed')
        assert hasattr(sentinel_provider, 'SEEDS')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
