#!/bin/sh
#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

set -ex
CONF="/etc/apt/apt.conf"
MY_PROXY_URL='"http://192.109.76.93:8080"'

# Delete lines
sed -i -r '/^Acquire::http::proxy .*$/d' $CONF
sed -i -r '/^Acquire::https::proxy .*$/d' $CONF
sed -i -r '/^Acquire::ftp::proxy .*$/d' $CONF

cat <<END >>$CONF
Acquire::http::proxy $MY_PROXY_URL;
Acquire::https::proxy $MY_PROXY_URL;
Acquire::ftp::proxy $MY_PROXY_URL;
END