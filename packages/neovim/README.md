# sentinel.nvim

AI Safety validation for Neovim using the THSP protocol.

## Features

- **THSP Protocol**: Four-gate safety validation (Truth, Harm, Scope, Purpose)
- **Two Analysis Modes**:
  - Semantic (LLM-based): higher accuracy with OpenAI or Anthropic
  - Heuristic (pattern-based): works offline, no API required
    - Best for: quick local checks, offline usage, cost savings
    - Limitations: pattern-matching cannot catch all sophisticated attacks
- **Native Diagnostics**: Violations appear as Neovim diagnostics
- **Alignment Seeds**: Insert pre-built safety prompts directly into your files
- **Health Check**: Built-in `:checkhealth sentinel` support

## Installation

### lazy.nvim (recommended)

```lua
{
  'sentinel-seed/sentinel',
  opts = {
    semantic_mode = true,
    llm_provider = 'openai',
    -- openai_api_key = 'sk-...', -- or use OPENAI_API_KEY env var
  },
}
```

### packer.nvim

```lua
use {
  'sentinel-seed/sentinel',
  config = function()
    require('sentinel').setup({
      semantic_mode = true,
      llm_provider = 'openai',
    })
  end
}
```

### vim-plug

```vim
Plug 'sentinel-seed/sentinel'

" In your init.lua or after/plugin:
lua require('sentinel').setup({})
```

### Manual

```bash
git clone https://github.com/sentinel-seed/sentinel \
  ~/.local/share/nvim/site/pack/plugins/start/sentinel
```

## Configuration

```lua
require('sentinel').setup({
  -- Analysis mode: true = semantic (LLM), false = heuristic
  semantic_mode = true,

  -- LLM provider: 'openai' or 'anthropic'
  llm_provider = 'openai',

  -- API keys (can also use environment variables)
  openai_api_key = nil,    -- or set OPENAI_API_KEY
  anthropic_api_key = nil, -- or set ANTHROPIC_API_KEY

  -- Auto-analyze on text change
  auto_analyze = false,

  -- Debounce delay for auto-analyze (ms)
  debounce_ms = 500,

  -- Filetypes to analyze
  filetypes = { '*' },

  -- Enable default keymaps
  default_keymaps = false,

  -- Default keymap bindings (if default_keymaps = true)
  keymaps = {
    analyze = '<leader>sa',
    analyze_buffer = '<leader>sA',
    insert_seed = '<leader>si',
    clear = '<leader>sc',
    toggle = '<leader>st',
  },

  -- Diagnostic severity for each gate
  severity = {
    truth = vim.diagnostic.severity.ERROR,
    harm = vim.diagnostic.severity.ERROR,
    scope = vim.diagnostic.severity.WARN,
    purpose = vim.diagnostic.severity.WARN,
  },

  -- Show virtual text for diagnostics
  virtual_text = true,
})
```

## Commands

| Command | Description |
|---------|-------------|
| `:SentinelAnalyze` | Analyze current line or selection |
| `:SentinelAnalyzeBuffer` | Analyze entire buffer |
| `:SentinelInsertSeed [variant]` | Insert alignment seed (standard/minimal) |
| `:SentinelClear` | Clear all diagnostics |
| `:SentinelToggle` | Toggle on/off |
| `:SentinelStatus` | Show status window |

## Keymappings

### Using `<Plug>` mappings (recommended)

```lua
vim.keymap.set('n', '<leader>a', '<Plug>(SentinelAnalyze)')
vim.keymap.set('v', '<leader>a', '<Plug>(SentinelAnalyze)')
vim.keymap.set('n', '<leader>A', '<Plug>(SentinelAnalyzeBuffer)')
vim.keymap.set('n', '<leader>si', '<Plug>(SentinelInsertSeed)')
vim.keymap.set('n', '<leader>sc', '<Plug>(SentinelClear)')
vim.keymap.set('n', '<leader>st', '<Plug>(SentinelToggle)')
```

### Available `<Plug>` mappings

- `<Plug>(SentinelAnalyze)` - Analyze line/selection
- `<Plug>(SentinelAnalyzeBuffer)` - Analyze buffer
- `<Plug>(SentinelInsertSeed)` - Insert standard seed
- `<Plug>(SentinelInsertSeedMinimal)` - Insert minimal seed
- `<Plug>(SentinelClear)` - Clear diagnostics
- `<Plug>(SentinelToggle)` - Toggle on/off

## THSP Protocol

The THSP protocol validates content through four gates:

| Gate | Question | Severity |
|------|----------|----------|
| **Truth** | Does this involve deception? | ERROR |
| **Harm** | Could this cause harm? | ERROR |
| **Scope** | Is this within boundaries? | WARN |
| **Purpose** | Does this serve legitimate benefit? | WARN |

All gates must pass for content to be considered safe.

## Analysis Modes

### Semantic Mode (default)

Uses OpenAI or Anthropic LLMs for deep semantic understanding.

```lua
require('sentinel').setup({
  semantic_mode = true,
  llm_provider = 'openai', -- or 'anthropic'
})
```

Set your API key via environment variable:

```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Heuristic Mode

Pattern-based analysis that works offline.

```lua
require('sentinel').setup({
  semantic_mode = false,
})
```

## Health Check

Verify your installation:

```vim
:checkhealth sentinel
```

## Alignment Seeds

Insert alignment seeds to configure AI behavior:

```vim
:SentinelInsertSeed standard  " Full THSP protocol (~4K tokens)
:SentinelInsertSeed minimal   " Compact version (~2K tokens)
```

## Requirements

- Neovim >= 0.8.0 (0.9+ recommended for best experience)
- curl (for semantic analysis)
- OpenAI or Anthropic API key (for semantic analysis)

## Running Tests

Tests require [plenary.nvim](https://github.com/nvim-lua/plenary.nvim).

```bash
# Install plenary.nvim for testing
git clone https://github.com/nvim-lua/plenary.nvim \
  ~/.local/share/nvim/site/pack/testing/start/plenary.nvim

# Run all tests
cd packages/neovim
nvim --headless -c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua'}"
```

## License

MIT License - see [LICENSE](../../LICENSE)

## Links

- [Sentinel Website](https://sentinelseed.dev)
- [Documentation](https://sentinelseed.dev/docs)
- [PyPI Package](https://pypi.org/project/sentinelseed/)
- [npm Package](https://www.npmjs.com/package/@sentinelseed/core)
