-- sentinel.nvim - Configuration module

local M = {}

-- Default configuration
M.defaults = {
  -- Analysis mode: true = semantic (LLM), false = heuristic
  semantic_mode = true,

  -- LLM provider: 'openai' or 'anthropic'
  llm_provider = 'openai',

  -- API keys (can also be set via environment variables)
  openai_api_key = nil,
  anthropic_api_key = nil,

  -- Auto-analyze on text change
  auto_analyze = false,

  -- Debounce delay for auto-analyze (ms)
  debounce_ms = 500,

  -- Filetypes to analyze (glob patterns)
  filetypes = { '*' },

  -- Set up default keymaps
  default_keymaps = false,

  -- Default keymap bindings (only if default_keymaps = true)
  keymaps = {
    analyze = '<leader>sa',        -- Analyze current line/selection
    analyze_buffer = '<leader>sA', -- Analyze entire buffer
    insert_seed = '<leader>si',    -- Insert seed
    clear = '<leader>sc',          -- Clear diagnostics
    toggle = '<leader>st',         -- Toggle on/off
  },

  -- Diagnostic severity for violations
  severity = {
    truth = vim.diagnostic.severity.ERROR,
    harm = vim.diagnostic.severity.ERROR,
    scope = vim.diagnostic.severity.WARN,
    purpose = vim.diagnostic.severity.WARN,
  },

  -- Show virtual text for diagnostics
  virtual_text = true,

  -- Sign column symbols
  signs = {
    truth = '',
    harm = '',
    scope = '',
    purpose = '',
  },

  -- Highlight groups
  highlights = {
    truth = 'DiagnosticError',
    harm = 'DiagnosticError',
    scope = 'DiagnosticWarn',
    purpose = 'DiagnosticWarn',
  },
}

-- Current options (merged with defaults)
M.options = vim.deepcopy(M.defaults)

---Setup configuration with user options
---@param opts table|nil User configuration
function M.setup(opts)
  opts = opts or {}

  -- Merge user options with defaults
  M.options = vim.tbl_deep_extend('force', M.defaults, opts)

  -- Try to get API keys from environment if not set
  if not M.options.openai_api_key then
    M.options.openai_api_key = vim.env.OPENAI_API_KEY
  end

  if not M.options.anthropic_api_key then
    M.options.anthropic_api_key = vim.env.ANTHROPIC_API_KEY
  end

  -- Fall back to heuristic mode if no API keys available
  if M.options.semantic_mode then
    if M.options.llm_provider == 'openai' and not M.options.openai_api_key then
      M.options.semantic_mode = false
      vim.notify('Sentinel: No OpenAI API key, falling back to heuristic mode', vim.log.levels.WARN)
    elseif M.options.llm_provider == 'anthropic' and not M.options.anthropic_api_key then
      M.options.semantic_mode = false
      vim.notify('Sentinel: No Anthropic API key, falling back to heuristic mode', vim.log.levels.WARN)
    end
  end

  -- Set up diagnostic configuration
  M.setup_diagnostics()
end

---Configure vim.diagnostic for Sentinel
function M.setup_diagnostics()
  -- Define custom signs for each gate type
  for gate, symbol in pairs(M.options.signs) do
    local name = 'DiagnosticSignSentinel' .. gate:sub(1, 1):upper() .. gate:sub(2)
    vim.fn.sign_define(name, {
      text = symbol,
      texthl = M.options.highlights[gate],
      numhl = '',
    })
  end

  -- Configure diagnostic display
  vim.diagnostic.config({
    virtual_text = M.options.virtual_text and {
      prefix = '●',
      source = 'if_many',
    } or false,
    signs = true,
    underline = true,
    update_in_insert = false,
    severity_sort = true,
  }, require('sentinel').ns)
end

---Get the appropriate API key for current provider
---@return string|nil
function M.get_api_key()
  if M.options.llm_provider == 'openai' then
    return M.options.openai_api_key
  elseif M.options.llm_provider == 'anthropic' then
    return M.options.anthropic_api_key
  end
  return nil
end

---Check if semantic mode is available
---@return boolean
function M.semantic_available()
  return M.options.semantic_mode and M.get_api_key() ~= nil
end

return M
