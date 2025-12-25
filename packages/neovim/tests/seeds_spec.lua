-- Tests for sentinel.nvim seeds module
-- Run with: nvim --headless -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"

local seeds = require('sentinel.seeds')

describe('seeds', function()
  describe('variants', function()
    it('has standard seed', function()
      assert.is_not_nil(seeds.standard)
      assert.is_not_nil(seeds.variants.standard)
    end)

    it('has minimal seed', function()
      assert.is_not_nil(seeds.minimal)
      assert.is_not_nil(seeds.variants.minimal)
    end)
  end)

  describe('get', function()
    it('returns standard seed', function()
      local seed = seeds.get('standard')
      assert.is_not_nil(seed)
      assert.is_true(#seed > 100)
    end)

    it('returns minimal seed', function()
      local seed = seeds.get('minimal')
      assert.is_not_nil(seed)
      assert.is_true(#seed > 100)
    end)

    it('returns nil for unknown variant', function()
      local seed = seeds.get('unknown')
      assert.is_nil(seed)
    end)
  end)

  describe('list', function()
    it('returns list of variants', function()
      local variants = seeds.list()
      assert.is_table(variants)
      assert.is_true(#variants >= 2)
    end)

    it('includes standard and minimal', function()
      local variants = seeds.list()
      local has_standard = false
      local has_minimal = false
      for _, v in ipairs(variants) do
        if v == 'standard' then has_standard = true end
        if v == 'minimal' then has_minimal = true end
      end
      assert.is_true(has_standard)
      assert.is_true(has_minimal)
    end)
  end)

  describe('seed content', function()
    it('standard seed contains THSP', function()
      local seed = seeds.get('standard')
      assert.is_truthy(seed:match('THSP'))
    end)

    it('standard seed contains all four gates', function()
      local seed = seeds.get('standard')
      assert.is_truthy(seed:match('TRUTH'))
      assert.is_truthy(seed:match('HARM'))
      assert.is_truthy(seed:match('SCOPE'))
      assert.is_truthy(seed:match('PURPOSE'))
    end)

    it('minimal seed contains all four gates', function()
      local seed = seeds.get('minimal')
      assert.is_truthy(seed:match('TRUTH'))
      assert.is_truthy(seed:match('HARM'))
      assert.is_truthy(seed:match('SCOPE'))
      assert.is_truthy(seed:match('PURPOSE'))
    end)

    it('minimal seed is shorter than standard', function()
      local standard = seeds.get('standard')
      local minimal = seeds.get('minimal')
      assert.is_true(#minimal < #standard)
    end)
  end)
end)
