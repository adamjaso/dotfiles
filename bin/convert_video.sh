#!/bin/bash

nproc=2

convert() {
    local inf="${1}"
    local outf="converted/${inf%.*}.mp4"
    local logf="logs/${inf%.*}.log"
    case "${inf##*.}" in
        #avi)    out_vcodec=copy ; out_acodec=copy ;;
        *)      out_vcodec=h264 ; out_acodec=aac ;;
    esac
    mkdir -p "$(dirname "${outf}")" "$(dirname "${logf}")"
    t=$(date +%s)
    echo "=> $(date "+%m%d %H:%M:%S")  converting '${inf}'"
    if [ ! -f "${outf}" ] ; then
        #ffmpeg -y -i "${inf}" -c:v h264 -c:a mp3 "${outf}" >"${logf}" 2>&1
        #ffmpeg -y -i "${inf}" -c:v h264 -c:a aac "${outf}" >"${logf}" 2>&1
        ffmpeg -y -i "${inf}" -strict -2 -c:v "${out_vcodec}" -c:a "${out_acodec}" "${outf}" >"${logf}" 2>&1
    else
        echo "=> $(date "+%m%d %H:%M:%S")  skipping ${outf}"
    fi
    echo "=> $(date "+%m%d %H:%M:%S")  converted  '${outf}' in $(($(date +%s)-t)) seconds"
}

trap 'kill $(jobs -p)' 0 15

while read f ; do
    convert "$f" &
    while [[ $(jobs -r | wc -l) -gt ${nproc} ]]; do
        wait -n
    done
done

wait -f
