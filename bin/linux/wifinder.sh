#!/bin/bash

iface=${1} ; shift
search='.*'
n=1
freq=2
header=
while [ $# -gt 0 ] ; do
    case $1 in
        -n)           n="$2" ;          shift ;;
        -s|--search)  search="$2" ;     shift ;;
        -f|--freq)    freq="$2" ;       shift ;;
        --header)     header=t ;;
        -h|--help)    cat <<EOF
usage: $(basename $0) interface [-n NUM_RESULTS] [-s|--search ESSID_REGEX] [-f|--freq 2|5] [--header] [-h|--help]
EOF
                     exit 1 ;;
    esac
    shift
done

current=

add_line() {
    [[ "$1" = *"Address:"* ]] && {
        echo "$current"
        current="${1#Cell [1234567890]*- *}"
    } || {
        current="$current $1"
    }
}

#iw dev ${iface} scan | \
iwlist ${iface} scanning | \
    grep -E 'Address|Frequency|Channel|ESSID|Quality' | \
    while read line ; do
        add_line "$line"
    done | \
    grep -E "${search}" | \
    sort -t'=' -gk3 | \
    { [ ${n} -gt 0 ] && tail -n${n} || cat ; } | \
    { [ ${freq} -gt 0 ] && grep -E "Frequency:${freq}" || cat ; } | \
    { [ -z ${header} ] || echo "ADDRESS CHANNEL FREQUENCY QUALITY SIGNAL ESSID" ; cat ; } | \
    sed -E '
s/\x/\\x/g;
s/ESSID:\s*//;
s/Address:\s*//;
s/Quality=\s*//;
s/Signal level=(-?[0-9]+)\s*dBm/\1/;
s/Channel:\s*//;
s/Frequency:\s*([0-9.]+)\s*GHz(\s*\([^)]+\))?/\1/;
'
