--vim.diagnostic.config({
--  virtual_text = false
--})
local lspconfig = require('lspconfig')
lspconfig.lua_ls.setup{
  diagnostics = true,
}
lspconfig.gopls.setup{
  --diagnostics = true,
  --root_dir = require('lspconfig').util.root_pattern(".git","go.mod","."),
  --filetypes = { "go", "gomod", "gowork", "gotmpl" },
  settings = {
    gopls = {
      completeUnimported = true,
      usePlaceholders = true,
      analyses = {
        unusedparams = true,
      },
    },
  },
}
lspconfig.pyright.setup{
  settings = {
    python = {
      analysis = {
        typeCheckingMode = "off",
      },
    },
  },
}
lspconfig.pylsp.setup{
  settings = {
    pylsp = {
      plugins = {
        black = { enabled = true },
	isort = { enabled = true, profile = "black" },
        pycodestyle = { enabled = true, maxLineLength = 200 }
      },
    },
  },
} --pip install python-lsp-server
lspconfig.volar.setup{
  filetypes = {'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue', 'json'},
  init_options = {
    typescript = {
      -- replace with your global TypeScript library path
      tsdk = '/usr/lib/node_modules/typescript/lib'
    }
  }
}
--lspconfig.vuels.setup{ }
lspconfig.ts_ls.setup{
  init_options = {
    plugins = {
      {
        name = "@vue/typescript-plugin",
        location = "/usr/lib/node_modules/@vue/typescript-plugin",
        languages = {"javascript", "typescript", "vue"},
      },
    },
  },
  filetypes = {
    "javascript",
    "typescript",
    "vue",
  },
}

-- Global mappings.
-- See `:help vim.diagnostic.*` for documentation on any of the below functions
vim.keymap.set('n', '<space>e', vim.diagnostic.open_float)
vim.keymap.set('n', '[d', vim.diagnostic.goto_prev)
vim.keymap.set('n', ']d', vim.diagnostic.goto_next)
vim.keymap.set('n', '<space>q', vim.diagnostic.setloclist)

-- Autoformat on save
vim.api.nvim_create_augroup('AutoFormatting', {})

-- Golang -- https://www.reddit.com/r/neovim/comments/y9qv1w/autoformatting_on_save_with_vimlspbufformat_and/
vim.api.nvim_create_autocmd('BufWritePre', {
  pattern = '*.go',
  group = 'AutoFormatting',
  callback = function()
    vim.lsp.buf.format({ async = false })
  end,
})

-- Python -- https://stackoverflow.com/questions/77466697/how-to-automatically-format-on-save
vim.api.nvim_create_autocmd('BufWritePost', {
    pattern = '*.py',
    group = 'AutoFormatting',
    callback = function()
        vim.cmd('silent !black --quiet %')            
        vim.cmd('edit')
    end,
})

-- Use LspAttach autocommand to only map the following keys
-- after the language server attaches to the current buffer
vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('UserLspConfig', {}),
  callback = function(ev)
    -- Enable completion triggered by <c-x><c-o>
    vim.bo[ev.buf].omnifunc = 'v:lua.vim.lsp.omnifunc'

    -- Buffer local mappings.
    -- See `:help vim.lsp.*` for documentation on any of the below functions
    local opts = { buffer = ev.buf }
    vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts)
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
    vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
    vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts)
    vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts)
    vim.keymap.set('n', '<space>wa', vim.lsp.buf.add_workspace_folder, opts)
    vim.keymap.set('n', '<space>wr', vim.lsp.buf.remove_workspace_folder, opts)
    vim.keymap.set('n', '<space>wl', function()
      print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
    end, opts)
    vim.keymap.set('n', '<space>D', vim.lsp.buf.type_definition, opts)
    vim.keymap.set('n', '<space>rn', vim.lsp.buf.rename, opts)
    vim.keymap.set({ 'n', 'v' }, '<space>ca', vim.lsp.buf.code_action, opts)
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts)
    vim.keymap.set('n', '<space>f', function()
      vim.lsp.buf.format { async = true }
    end, opts)
  end,
})
