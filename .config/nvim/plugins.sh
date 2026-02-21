#!/bin/bash

plugin_clone_dir=~/.local/share/nvim/site/pack/plugins/start
plugin_list_file=~/.config/nvim/plugins.txt

list-current() {
    find "${plugin_clone_dir}" -type d -name .git | sed 's:/\.git::'
}

list-file() {
    cat "${plugin_list_file}"
}

pull() {
    local repo="${1}"
    echo "== pulling '${repo##*/}' in '${repo%/*}' ==" >&2
    pushd "${repo}" >/dev/null
    git pull -q
    popd >/dev/null
}

pull-all() {
    while read repo ; do 
        pull "${repo}"
    done < <(list-current)
}

clone() {
    mkdir -p "${plugin_clone_dir}"
    local clone_dir="${plugin_clone_dir}/$(basename "${1}")"
    if [ ! -d "${clone_dir}" ] ; then
        echo "== cloning '${repo#https://*/}' to '${clone_dir}' ==" >&2
        git clone "${1}" "${clone_dir}"
    else
        echo "== already cloned '${repo#https://*/}' to '${clone_dir}' ==" >&2
    fi
}

clone-all() {
    while read repo ; do
        clone "${repo}"
    done < <(list-file)
}

action="${1}"
shift
case "${action}" in
    list-current|pull|pull-all|clone|clone-all) "${action}" ${@} ;;
    -h) echo "$(basename $0) list-current|pull|pull-all|clone|clone-all [FLAGS]" ;;
esac
