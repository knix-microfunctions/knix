#!/bin/sh
docker logs -f Management | grep -v __mfn_tracing | grep -v __mfn_progress | grep admin@management | awk -F"," '{out=""; for(i=10;i<=NF;i++){out=out$i","}; print out}'