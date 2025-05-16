local ensure_packer = function()
  local fn = vim.fn
  local install_path = fn.stdpath('data')..'/site/pack/packer/start/packer.nvim'
  if fn.empty(fn.glob(install_path)) > 0 then
    fn.system({'git', 'clone', '--depth', '1', 'https://github.com/wbthomason/packer.nvim', install_path})
    vim.cmd [[packadd packer.nvim]]
    return true
  end
  return false
end

local packer_bootstrap = ensure_packer()

return require('packer').startup(function(use)
  use 'wbthomason/packer.nvim'
  use 'nvim-tree/nvim-web-devicons'
  use 'nvim-tree/nvim-tree.lua'
  use 'nvim-treesitter/nvim-treesitter'
  use 'nvim-lualine/lualine.nvim'
  use 'windwp/nvim-autopairs'
  use 'Tsuzat/NeoSolarized.nvim'

  -- git blame
  -- use 'f-person/git-blame.nvim'
  use 'FabijanZulj/blame.nvim'

  -- completion
  use 'sar/cmp-lsp.nvim' -- might still need this...
  use 'neovim/nvim-lspconfig'
  use 'hrsh7th/nvim-cmp'
  use 'ray-x/lsp_signature.nvim'
  use 'nvim-lua/plenary.nvim' -- lua completion
  use {
	"L3MON4D3/LuaSnip",
	-- follow latest release.
	tag = "v2.*", -- Replace <CurrentMajor> by the latest released major (first number of latest release)
	-- install jsregexp (optional!:).
	run = "make install_jsregexp"
  }

  -- fuzzy find
  use 'nvim-telescope/telescope.nvim'

  -- golang compile issue viewer
  use {'folke/trouble.nvim', config = function() require("trouble").setup{} end } -- shows golang errors window
  use {"stevearc/aerial.nvim", config = function() require("aerial").setup() end } -- shows list of functions on right side window

  -- unused
  -- use 'hrsh7th/cmp-buffer' -- don't think I'm using this
  -- use 'hrsh7th/cmp-path' -- don't think I'm using this
  -- use 'saadparwaiz1/cmp_luasnip' -- don't think I'm using this
  -- use 'neoclide/coc.nvim' -- memory hog (nodejs)
  -- use { 'neoclide/coc.nvim', branch = 'master', run = 'npm ci' }

  -- Automatically set up your configuration after cloning packer.nvim
  -- Put this at the end after all plugins
  if packer_bootstrap then
    require('packer').sync()
  end
end)
