#!/bin/sh
set -ex
cargo build --release
RUST_BACKTRACE=1 RUST_LOG=info TRIGGERS_FRONTEND_PORT="8080" MANAGEMENT_URL="http://httpbin.org/post" MANAGEMENT_ACTION="triggersFrontendStatus" MANAGEMENT_UPDATE_INTERVAL_SEC="60" HOST_IP=`hostname -i` ./target/release/TriggersFrontend
