execute pathogen#infect()
"mkdir -p ~/.vim/{bundle,autoload,ftplugin}
"# install pathogen
"curl -LSso ~/.vim/autoload/pathogen.vim https://tpo.pe/pathogen.vim
"#
"# install auto-pairs
"git clone git://github.com/jiangmiao/auto-pairs.git ~/.vim/bundle/auto-pairs
"#
"# install nerdtree
"git clone https://github.com/scrooloose/NERDTree.git ~/.vim/bundle/NERDTree
"#
"# install fugitive
"git clone https://github.com/tpope/vim-fugitive.git ~/.vim/bundle/vim-fugitive

" nerdtree
filetype plugin indent on
let NERDTreeIgnore = ['\.pyc$', '__pycache__$', '\.egg-info$', '\.DS_Store$']
let mapleader = ","
nmap <leader>ne :NERDTree

" key mappings
nnoremap <C-J> <C-W><C-J>
nnoremap <C-K> <C-W><C-K>
nnoremap <C-L> <C-W><C-L>
nnoremap <C-H> <C-W><C-H>
imap <C-Return> <CR><CR><C-o>k<Tab>
"vmap <C-c> :w !pbcopy<CR><CR>
map ,, :vertical resize +5<CR>
map .. :vertical resize -5<CR>
map << :resize +5<CR>
map >> :resize -5<CR>

" general
set list hls nu et ai si ru backspace=indent,eol,start background=dark sw=4 sts=4 ts=4 cc=80 ls=2
syntax enable

" file type formatting
au BufNewFile,BufRead *.sls,*.j2 set ft=jinja
au FileType javascript setlocal sw=2 ts=2 sts=2 cc=120
au FileType python setlocal sw=4 sts=4 cc=80
au FileType html setlocal sw=2 ts=2 sts=2 cc=120 nolist
au FileType yaml setlocal sw=2 ts=2 sts=2 cc=120
au FileType md setlocal sw=2 ts=2 sts=2 cc=120
au FileType go setlocal nolist
