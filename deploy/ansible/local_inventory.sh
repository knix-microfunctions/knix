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

HOSTNAME=$(/bin/hostname -f)
# get hostip via ping, so that it is using the public IP
HOSTIP=$(ping $HOSTNAME -c 1 | head -1 | awk '{print $3}' | awk 'BEGIN {FS="[()]"}; {print $2}')

# ansible_ssh_host will be utilized to map the IP addresses to the publicly available IP address
# (i.e., the one connected by ansible master)
cat <<END >inventory.cfg
[riak]
$HOSTNAME ansible_ssh_host=$HOSTIP

[elasticsearch]
$HOSTNAME ansible_ssh_host=$HOSTIP

[management]
$HOSTNAME ansible_ssh_host=$HOSTIP

[nginx]
$HOSTNAME ansible_ssh_host=$HOSTIP

[triggers_frontend]
$HOSTNAME ansible_ssh_host=$HOSTIP
END
