#!/bin/bash -ex

riak-admin cluster status
riak-admin cluster leave
riak-admin cluster plan
riak-admin cluster commit

while `riak ping` == "pong"
do echo "Waiting on shutdown ..."
   sleep 10
done