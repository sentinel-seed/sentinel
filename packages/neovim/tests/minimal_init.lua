-- Minimal init for running tests
-- This sets up the runtime path for the plugin

local plugin_dir = vim.fn.fnamemodify(vim.fn.getcwd(), ':h')
vim.opt.rtp:append(plugin_dir)

-- Plenary is required for tests
-- Install: git clone https://github.com/nvim-lua/plenary.nvim ~/.local/share/nvim/site/pack/testing/start/plenary.nvim
vim.cmd([[packadd plenary.nvim]])
