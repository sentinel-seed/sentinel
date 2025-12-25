-- Tests for sentinel.nvim config module
-- Run with: nvim --headless -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"

local config = require('sentinel.config')

describe('config', function()
  describe('defaults', function()
    it('has semantic_mode defaulting to true', function()
      assert.is_true(config.defaults.semantic_mode)
    end)

    it('has openai as default provider', function()
      assert.equals('openai', config.defaults.llm_provider)
    end)

    it('has auto_analyze defaulting to false', function()
      assert.is_false(config.defaults.auto_analyze)
    end)

    it('has 500ms default debounce', function()
      assert.equals(500, config.defaults.debounce_ms)
    end)

    it('has all four gates in severity config', function()
      assert.is_not_nil(config.defaults.severity.truth)
      assert.is_not_nil(config.defaults.severity.harm)
      assert.is_not_nil(config.defaults.severity.scope)
      assert.is_not_nil(config.defaults.severity.purpose)
    end)
  end)

  describe('setup', function()
    before_each(function()
      -- Reset to defaults
      config.options = vim.deepcopy(config.defaults)
    end)

    it('merges user options with defaults', function()
      config.setup({ debounce_ms = 1000 })
      assert.equals(1000, config.options.debounce_ms)
      -- Other defaults should remain
      assert.equals('openai', config.options.llm_provider)
    end)

    it('handles nil opts', function()
      assert.has_no.errors(function()
        config.setup(nil)
      end)
    end)

    it('handles empty opts', function()
      assert.has_no.errors(function()
        config.setup({})
      end)
    end)
  end)

  describe('get_api_key', function()
    before_each(function()
      config.options = vim.deepcopy(config.defaults)
    end)

    it('returns nil when no key configured', function()
      config.options.llm_provider = 'openai'
      config.options.openai_api_key = nil
      assert.is_nil(config.get_api_key())
    end)

    it('returns openai key when provider is openai', function()
      config.options.llm_provider = 'openai'
      config.options.openai_api_key = 'test-key'
      assert.equals('test-key', config.get_api_key())
    end)

    it('returns anthropic key when provider is anthropic', function()
      config.options.llm_provider = 'anthropic'
      config.options.anthropic_api_key = 'test-key'
      assert.equals('test-key', config.get_api_key())
    end)
  end)

  describe('semantic_available', function()
    before_each(function()
      config.options = vim.deepcopy(config.defaults)
    end)

    it('returns false when semantic_mode is off', function()
      config.options.semantic_mode = false
      assert.is_false(config.semantic_available())
    end)

    it('returns false when no api key', function()
      config.options.semantic_mode = true
      config.options.openai_api_key = nil
      assert.is_false(config.semantic_available())
    end)

    it('returns true when semantic mode and key available', function()
      config.options.semantic_mode = true
      config.options.llm_provider = 'openai'
      config.options.openai_api_key = 'test-key'
      assert.is_true(config.semantic_available())
    end)
  end)
end)
