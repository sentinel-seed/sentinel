-- sentinel.nvim - AI Safety validation using THSP protocol
-- https://sentinelseed.dev

-- Prevent double loading
if vim.g.loaded_sentinel then
  return
end
vim.g.loaded_sentinel = true

-- Create user commands (defer require to command execution for lazy loading)

vim.api.nvim_create_user_command('SentinelAnalyze', function(opts)
  local sentinel = require('sentinel')
  local range = nil
  if opts.range > 0 then
    range = { opts.line1, opts.line2 }
  end
  sentinel.analyze(range)
end, {
  range = true,
  desc = 'Analyze text for THSP safety violations',
})

vim.api.nvim_create_user_command('SentinelAnalyzeBuffer', function()
  local sentinel = require('sentinel')
  sentinel.analyze_buffer()
end, {
  desc = 'Analyze entire buffer for THSP safety violations',
})

vim.api.nvim_create_user_command('SentinelInsertSeed', function(opts)
  local sentinel = require('sentinel')
  local variant = opts.args ~= '' and opts.args or 'standard'
  sentinel.insert_seed(variant)
end, {
  nargs = '?',
  complete = function()
    return { 'standard', 'minimal' }
  end,
  desc = 'Insert Sentinel alignment seed at cursor',
})

vim.api.nvim_create_user_command('SentinelClear', function()
  local sentinel = require('sentinel')
  sentinel.clear_diagnostics()
end, {
  desc = 'Clear all Sentinel diagnostics',
})

vim.api.nvim_create_user_command('SentinelStatus', function()
  local sentinel = require('sentinel')
  sentinel.show_status()
end, {
  desc = 'Show Sentinel configuration status',
})

vim.api.nvim_create_user_command('SentinelToggle', function()
  local sentinel = require('sentinel')
  sentinel.toggle()
end, {
  desc = 'Toggle Sentinel analysis on/off',
})

-- Create <Plug> mappings for user customization

vim.keymap.set('n', '<Plug>(SentinelAnalyze)', function()
  require('sentinel').analyze()
end, { desc = 'Analyze current line for THSP violations' })

vim.keymap.set('v', '<Plug>(SentinelAnalyze)', function()
  require('sentinel').analyze_visual()
end, { desc = 'Analyze selection for THSP violations' })

vim.keymap.set('n', '<Plug>(SentinelAnalyzeBuffer)', function()
  require('sentinel').analyze_buffer()
end, { desc = 'Analyze entire buffer for THSP violations' })

vim.keymap.set('n', '<Plug>(SentinelInsertSeed)', function()
  require('sentinel').insert_seed('standard')
end, { desc = 'Insert standard Sentinel seed' })

vim.keymap.set('n', '<Plug>(SentinelInsertSeedMinimal)', function()
  require('sentinel').insert_seed('minimal')
end, { desc = 'Insert minimal Sentinel seed' })

vim.keymap.set('n', '<Plug>(SentinelClear)', function()
  require('sentinel').clear_diagnostics()
end, { desc = 'Clear Sentinel diagnostics' })

vim.keymap.set('n', '<Plug>(SentinelToggle)', function()
  require('sentinel').toggle()
end, { desc = 'Toggle Sentinel on/off' })
