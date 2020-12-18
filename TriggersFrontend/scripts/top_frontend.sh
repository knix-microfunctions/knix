#!/bin/sh
set -ex
TPID=`ps -ef | grep TriggersFrontend | grep -v 'grep' | head -1 | awk '{print $2}'`
if [ -n "$TPID" ]; then
    top -p $TPID
else
    echo "TriggersFrontend process not found"
fi
