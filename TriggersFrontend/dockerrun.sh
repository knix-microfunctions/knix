#!/bin/sh
set -ex
export RUST_BACKTRACE=1 
export RUST_LOG=${TRIGGERS_FRONTEND_LOG_LEVEL:-"info"}
export TRIGGERS_FRONTEND_PORT=${TRIGGERS_FRONTEND_PORT:-"4997"} 
export MANAGEMENT_URL=${MANAGEMENT_URL:-"http://httpbin.org/post"}
export MANAGEMENT_ACTION=${MANAGEMENT_ACTION:-"triggersFrontendStatus"} 
export MANAGEMENT_UPDATE_INTERVAL_SEC=${MANAGEMENT_UPDATE_INTERVAL_SEC:-"60"}  
export HOST_IP=${HOST_IP:-`hostname -i | awk '{print $1}'`}
/opt/mfn/triggers_frontend/TriggersFrontend
