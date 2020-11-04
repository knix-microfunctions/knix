#!/bin/sh
set -ex
cargo build --release
RUST_BACKTRACE=1 RUST_LOG=${TRIGGERS_FRONTEND_LOG_LEVEL:-"info"} TRIGGERS_FRONTEND_PORT=${TRIGGERS_FRONTEND_PORT:-"4997"} MANAGEMENT_URL=${MANAGEMENT_URL:-"http://httpbin.org/post"} MANAGEMENT_ACTION=${MANAGEMENT_ACTION:-"triggersFrontendStatus"} MANAGEMENT_UPDATE_INTERVAL_SEC=${MANAGEMENT_UPDATE_INTERVAL_SEC:-"60"} HOST_IP=${HOST_IP:-`hostname -i | awk '{print $1}'`} ./target/release/TriggersFrontend
