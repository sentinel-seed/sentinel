-- sentinel.nvim - Health check module
-- Run with :checkhealth sentinel

local M = {}

local health = vim.health

function M.check()
  health.start('Sentinel AI Safety')

  -- Check Neovim version
  local nvim_version = vim.version()
  if nvim_version.major == 0 and nvim_version.minor < 9 then
    health.warn('Neovim 0.9+ recommended for best experience')
  else
    health.ok(string.format('Neovim version: %d.%d.%d', nvim_version.major, nvim_version.minor, nvim_version.patch))
  end

  -- Check if plugin is loaded
  local ok, sentinel = pcall(require, 'sentinel')
  if ok then
    health.ok('sentinel.nvim loaded successfully')
  else
    health.error('Failed to load sentinel.nvim', { 'Check installation', 'Run :Lazy sync if using lazy.nvim' })
    return
  end

  -- Check configuration
  local config = require('sentinel.config')
  health.ok('Configuration loaded')

  -- Check analysis mode
  if config.options.semantic_mode then
    health.info('Analysis mode: Semantic (LLM-based, ~90% accuracy)')
  else
    health.info('Analysis mode: Heuristic (pattern-based, ~50% accuracy)')
  end

  -- Check LLM provider
  if config.options.semantic_mode then
    health.info('LLM Provider: ' .. config.options.llm_provider)

    -- Check API keys
    if config.options.llm_provider == 'openai' then
      if config.options.openai_api_key then
        -- Mask the key
        local key = config.options.openai_api_key
        local masked = key:sub(1, 7) .. '...' .. key:sub(-4)
        health.ok('OpenAI API key configured: ' .. masked)
      else
        health.warn('OpenAI API key not configured', {
          'Set OPENAI_API_KEY environment variable',
          'Or configure via setup({ openai_api_key = "..." })',
          'Falling back to heuristic mode',
        })
      end
    elseif config.options.llm_provider == 'anthropic' then
      if config.options.anthropic_api_key then
        local key = config.options.anthropic_api_key
        local masked = key:sub(1, 7) .. '...' .. key:sub(-4)
        health.ok('Anthropic API key configured: ' .. masked)
      else
        health.warn('Anthropic API key not configured', {
          'Set ANTHROPIC_API_KEY environment variable',
          'Or configure via setup({ anthropic_api_key = "..." })',
          'Falling back to heuristic mode',
        })
      end
    end
  end

  -- Check curl availability (needed for API calls)
  local curl_ok = vim.fn.executable('curl') == 1
  if curl_ok then
    health.ok('curl is available')
  else
    health.error('curl not found', {
      'Install curl for semantic analysis',
      'On macOS: brew install curl',
      'On Ubuntu: sudo apt install curl',
      'On Windows: curl is included in Windows 10+',
    })
  end

  -- Check seeds
  local seeds = require('sentinel.seeds')
  local variants = seeds.list()
  health.ok(string.format('Seeds loaded: %s', table.concat(variants, ', ')))

  -- Check diagnostic namespace
  if sentinel.ns then
    health.ok('Diagnostic namespace created: ' .. sentinel.ns)
  else
    health.warn('Diagnostic namespace not created')
  end

  -- Check plugin state
  if sentinel.enabled then
    health.ok('Sentinel is enabled')
  else
    health.info('Sentinel is currently disabled (use :SentinelToggle to enable)')
  end

  -- Show configuration summary
  health.info('')
  health.info('Configuration Summary:')
  health.info('  auto_analyze: ' .. tostring(config.options.auto_analyze))
  health.info('  debounce_ms: ' .. config.options.debounce_ms)
  health.info('  default_keymaps: ' .. tostring(config.options.default_keymaps))
  health.info('  filetypes: ' .. table.concat(config.options.filetypes, ', '))

  -- Commands available
  health.info('')
  health.info('Available Commands:')
  health.info('  :SentinelAnalyze       - Analyze current line/selection')
  health.info('  :SentinelAnalyzeBuffer - Analyze entire buffer')
  health.info('  :SentinelInsertSeed    - Insert alignment seed')
  health.info('  :SentinelClear         - Clear diagnostics')
  health.info('  :SentinelToggle        - Toggle on/off')
  health.info('  :SentinelStatus        - Show status')

  -- Keybindings
  if config.options.default_keymaps then
    health.info('')
    health.info('Default Keymaps (enabled):')
    for action, key in pairs(config.options.keymaps) do
      if key then
        health.info(string.format('  %s: %s', action, key))
      end
    end
  else
    health.info('')
    health.info('Default keymaps disabled. Use <Plug> mappings to set your own:')
    health.info('  <Plug>(SentinelAnalyze)')
    health.info('  <Plug>(SentinelAnalyzeBuffer)')
    health.info('  <Plug>(SentinelInsertSeed)')
    health.info('  <Plug>(SentinelClear)')
    health.info('  <Plug>(SentinelToggle)')
  end
end

return M
