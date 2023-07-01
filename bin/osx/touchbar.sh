#!/bin/bash
# http://osxdaily.com/2017/01/11/manually-refresh-touch-bar-mac/
CMD=$1

[[ "$CMD" = "kill" ]] && killall ControlStrip && exit
[[ "$CMD" = "refresh" ]] && pkill "Touch Bar agent" && exit
echo "usage: ./$(basename $0) [ kill | refresh ]"
