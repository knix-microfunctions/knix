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

MY_PROXY_URL='"http://192.109.76.93:8080"'
MY_HOSTIP=`hostname -i | awk '{print $1}'`
MY_NO_PROXY='"127.0.0.1,localhost,alcatel-lucent.com,gitlabe1.ext.net.nokia.com,149.204.63.97/8,bls-calendar.rcs.alcatel-research.de,nok.it,149.204.179.178,"$(hostname)",$MY_HOSTIP"'

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


# Add lines
cat <<END >>$CONF
MY_HOSTIP=$MY_HOSTIP
MY_PROXY_URL=$MY_PROXY_URL
MY_NO_PROXY=$MY_NO_PROXY
HTTP_PROXY=$MY_PROXY_URL
HTTPS_PROXY=$MY_PROXY_URL
FTP_PROXY=$MY_PROXY_URL
http_proxy=$MY_PROXY_URL
https_proxy=$MY_PROXY_URL
ftp_proxy=$MY_PROXY_URL
no_proxy=$MY_NO_PROXY
NO_PROXY=$MY_NO_PROXY
export MY_HOSTIP HTTP_PROXY HTTPS_PROXY FTP_PROXY http_proxy https_proxy ftp_proxy no_proxy NO_PROXY
END

source $CONF

# Add lines
cat <<END >>$CONF2
MY_HOSTIP=$MY_HOSTIP
MY_PROXY_URL=$MY_PROXY_URL
MY_NO_PROXY=$MY_NO_PROXY
HTTP_PROXY=$MY_PROXY_URL
HTTPS_PROXY=$MY_PROXY_URL
FTP_PROXY=$MY_PROXY_URL
http_proxy=$MY_PROXY_URL
https_proxy=$MY_PROXY_URL
ftp_proxy=$MY_PROXY_URL
no_proxy=$MY_NO_PROXY
NO_PROXY=$MY_NO_PROXY
export MY_HOSTIP HTTP_PROXY HTTPS_PROXY FTP_PROXY http_proxy https_proxy ftp_proxy no_proxy NO_PROXY
END

source $CONF2
