#!/bin/bash
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

CONF="/etc/bash.bashrc"
# Delete lines
sed -i -r '/^MY_PROXY_URL=.*$/d' $CONF
sed -i -r '/^MY_NO_PROXY=.*$/d' $CONF
sed -i -r '/^HTTP_PROXY=.*$/d' $CONF
sed -i -r '/^HTTPS_PROXY=.*$/d' $CONF
sed -i -r '/^FTP_PROXY=.*$/d' $CONF
sed -i -r '/^http_proxy=.*$/d' $CONF
sed -i -r '/^https_proxy=.*$/d' $CONF
sed -i -r '/^ftp_proxy=.*$/d' $CONF
sed -i -r '/^no_proxy=.*$/d' $CONF
sed -i -r '/^NO_PROXY=.*$/d' $CONF
sed -i -r '/^export HTTP_PROXY HTTPS_PROXY FTP_PROXY .*$/d' $CONF


CONF2="/etc/profile"
# Delete lines
sed -i -r '/^MY_PROXY_URL=.*$/d' $CONF2
sed -i -r '/^MY_NO_PROXY=.*$/d' $CONF2
sed -i -r '/^HTTP_PROXY=.*$/d' $CONF2
sed -i -r '/^HTTPS_PROXY=.*$/d' $CONF2
sed -i -r '/^FTP_PROXY=.*$/d' $CONF2
sed -i -r '/^http_proxy=.*$/d' $CONF2
sed -i -r '/^https_proxy=.*$/d' $CONF2
sed -i -r '/^ftp_proxy=.*$/d' $CONF2
sed -i -r '/^no_proxy=.*$/d' $CONF2
sed -i -r '/^NO_PROXY=.*$/d' $CONF2
sed -i -r '/^export HTTP_PROXY HTTPS_PROXY FTP_PROXY .*$/d' $CONF2

source $CONF
source $CONF2