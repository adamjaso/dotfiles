-- Navigate vim panes better
vim.keymap.set('n', '<c-k>', ':wincmd k<CR>')
vim.keymap.set('n', '<c-j>', ':wincmd j<CR>')
vim.keymap.set('n', '<c-h>', ':wincmd h<CR>')
vim.keymap.set('n', '<c-l>', ':wincmd l<CR>')

vim.keymap.set('n', '<leader>ne', ':NvimTreeFindFileToggle')
vim.keymap.set('n', '<leader>xx', ':Trouble diagnostics<CR>')
vim.keymap.set('n', '<leader>bb', ':BlameToggle virtual<CR>')
vim.keymap.set("n", "<leader>a", '<cmd>AerialToggle!<CR>')

show_function_signature = require('lsp_signature').toggle_float_win
vim.keymap.set('n', '<C-S-Space>', show_function_signature, {
    silent = true,
    noremap = true,
    desc = 'toggle signature'
})

local builtin = require('telescope.builtin')
vim.keymap.set('n', '<leader>ff', builtin.find_files, {})
vim.keymap.set('n', '<leader>fg', builtin.live_grep, {})
vim.keymap.set('n', '<leader>fb', builtin.buffers, {})
vim.keymap.set('n', '<leader>fh', builtin.help_tags, {})
vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename)
