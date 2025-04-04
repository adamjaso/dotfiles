--depends on lspconfig.gopls.setup
require('lsp_signature').setup({
  bind = true, -- This is mandatory, otherwise border config won't get registered.
  handler_opts = {
    border = "rounded"
  }
})
