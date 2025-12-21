-- sentinel.nvim - AI Safety validation using THSP protocol
-- Main module

local M = {}

-- Module dependencies (lazy loaded)
local config = require('sentinel.config')
local analyzer = require('sentinel.analyzer')
local seeds = require('sentinel.seeds')

-- Diagnostic namespace
M.ns = vim.api.nvim_create_namespace('sentinel')

-- State
M.enabled = true

---Setup sentinel with user configuration
---@param opts table|nil User configuration options
function M.setup(opts)
  config.setup(opts)

  -- Set up autocommands if auto_analyze is enabled
  if config.options.auto_analyze then
    M.setup_autocommands()
  end

  -- Set up default keybindings if enabled
  if config.options.default_keymaps then
    M.setup_keymaps()
  end
end

---Set up autocommands for automatic analysis
function M.setup_autocommands()
  local group = vim.api.nvim_create_augroup('Sentinel', { clear = true })

  vim.api.nvim_create_autocmd({ 'TextChanged', 'TextChangedI' }, {
    group = group,
    pattern = config.options.filetypes,
    callback = function(args)
      if M.enabled and config.options.auto_analyze then
        -- Debounce: only analyze after user stops typing
        vim.defer_fn(function()
          if vim.api.nvim_buf_is_valid(args.buf) then
            M.analyze_buffer(args.buf)
          end
        end, config.options.debounce_ms)
      end
    end,
    desc = 'Sentinel auto-analyze on text change',
  })
end

---Set up default keymappings
function M.setup_keymaps()
  local opts = { silent = true }
  local mappings = config.options.keymaps

  if mappings.analyze then
    vim.keymap.set('n', mappings.analyze, '<Plug>(SentinelAnalyze)', opts)
    vim.keymap.set('v', mappings.analyze, '<Plug>(SentinelAnalyze)', opts)
  end

  if mappings.analyze_buffer then
    vim.keymap.set('n', mappings.analyze_buffer, '<Plug>(SentinelAnalyzeBuffer)', opts)
  end

  if mappings.insert_seed then
    vim.keymap.set('n', mappings.insert_seed, '<Plug>(SentinelInsertSeed)', opts)
  end

  if mappings.clear then
    vim.keymap.set('n', mappings.clear, '<Plug>(SentinelClear)', opts)
  end

  if mappings.toggle then
    vim.keymap.set('n', mappings.toggle, '<Plug>(SentinelToggle)', opts)
  end
end

---Analyze text at current cursor position or range
---@param range table|nil Optional {start_line, end_line}
function M.analyze(range)
  if not M.enabled then
    vim.notify('Sentinel is disabled', vim.log.levels.WARN)
    return
  end

  local bufnr = vim.api.nvim_get_current_buf()
  local lines
  local start_line

  if range then
    start_line = range[1]
    lines = vim.api.nvim_buf_get_lines(bufnr, range[1] - 1, range[2], false)
  else
    start_line = vim.api.nvim_win_get_cursor(0)[1]
    lines = vim.api.nvim_buf_get_lines(bufnr, start_line - 1, start_line, false)
  end

  local text = table.concat(lines, '\n')
  if text == '' then
    vim.notify('No text to analyze', vim.log.levels.INFO)
    return
  end

  analyzer.analyze_text(bufnr, text, start_line, M.ns)
end

---Analyze visual selection
function M.analyze_visual()
  if not M.enabled then
    vim.notify('Sentinel is disabled', vim.log.levels.WARN)
    return
  end

  -- Get visual selection
  local start_pos = vim.fn.getpos("'<")
  local end_pos = vim.fn.getpos("'>")
  local start_line = start_pos[2]
  local end_line = end_pos[2]

  M.analyze({ start_line, end_line })
end

---Analyze entire buffer
---@param bufnr number|nil Buffer number (default: current buffer)
function M.analyze_buffer(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()

  if not M.enabled then
    return
  end

  local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
  local text = table.concat(lines, '\n')

  if text == '' then
    return
  end

  analyzer.analyze_text(bufnr, text, 1, M.ns)
end

---Insert alignment seed at cursor position
---@param variant string Seed variant ('standard' or 'minimal')
function M.insert_seed(variant)
  variant = variant or 'standard'

  local seed = seeds.get(variant)
  if not seed then
    vim.notify('Unknown seed variant: ' .. variant, vim.log.levels.ERROR)
    return
  end

  -- Split seed into lines
  local seed_lines = vim.split(seed, '\n', { plain = true })

  -- Get current cursor position
  local row = vim.api.nvim_win_get_cursor(0)[1]

  -- Insert lines at cursor
  vim.api.nvim_buf_set_lines(0, row - 1, row - 1, false, seed_lines)

  vim.notify(string.format('Inserted %s seed (%d lines)', variant, #seed_lines), vim.log.levels.INFO)
end

---Clear all Sentinel diagnostics
---@param bufnr number|nil Buffer number (default: current buffer)
function M.clear_diagnostics(bufnr)
  bufnr = bufnr or vim.api.nvim_get_current_buf()
  vim.diagnostic.reset(M.ns, bufnr)
  vim.notify('Sentinel diagnostics cleared', vim.log.levels.INFO)
end

---Toggle Sentinel on/off
function M.toggle()
  M.enabled = not M.enabled

  if M.enabled then
    vim.notify('Sentinel enabled', vim.log.levels.INFO)
  else
    -- Clear all diagnostics when disabled
    for _, buf in ipairs(vim.api.nvim_list_bufs()) do
      if vim.api.nvim_buf_is_valid(buf) then
        vim.diagnostic.reset(M.ns, buf)
      end
    end
    vim.notify('Sentinel disabled', vim.log.levels.INFO)
  end
end

---Show current status
function M.show_status()
  local status = {
    'Sentinel AI Safety',
    '==================',
    '',
    'Status: ' .. (M.enabled and 'ENABLED' or 'DISABLED'),
    'Mode: ' .. (config.options.semantic_mode and 'Semantic (LLM)' or 'Heuristic'),
    '',
    'Configuration:',
    '  Auto-analyze: ' .. tostring(config.options.auto_analyze),
    '  Debounce: ' .. config.options.debounce_ms .. 'ms',
    '  Filetypes: ' .. table.concat(config.options.filetypes, ', '),
    '',
    'API Keys:',
    '  OpenAI: ' .. (config.options.openai_api_key and 'configured' or 'not set'),
    '  Anthropic: ' .. (config.options.anthropic_api_key and 'configured' or 'not set'),
    '',
    'Commands:',
    '  :SentinelAnalyze       - Analyze current line/selection',
    '  :SentinelAnalyzeBuffer - Analyze entire buffer',
    '  :SentinelInsertSeed    - Insert alignment seed',
    '  :SentinelClear         - Clear diagnostics',
    '  :SentinelToggle        - Toggle on/off',
    '  :SentinelStatus        - Show this status',
    '',
    'Run :checkhealth sentinel for detailed diagnostics',
  }

  -- Create floating window
  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, status)

  local width = 50
  local height = #status
  local opts = {
    relative = 'editor',
    width = width,
    height = height,
    col = (vim.o.columns - width) / 2,
    row = (vim.o.lines - height) / 2,
    style = 'minimal',
    border = 'rounded',
    title = ' Sentinel Status ',
    title_pos = 'center',
  }

  local win = vim.api.nvim_open_win(buf, true, opts)

  -- Close on any key
  vim.keymap.set('n', 'q', function()
    vim.api.nvim_win_close(win, true)
  end, { buffer = buf })

  vim.keymap.set('n', '<Esc>', function()
    vim.api.nvim_win_close(win, true)
  end, { buffer = buf })
end

return M
