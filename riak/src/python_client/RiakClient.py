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

import os
import socket
import time
import json
from riak import RiakClient

DLCLIENT = None

print("Waiting on Riak")
host,port = os.getenv("RIAK_CONNECT",socket.gethostname()+":8087").rsplit(":",1)
while True:
    try:
        print("Connecting to Riak server at "+host+":"+port)
        DLCLIENT = RiakClient(protocol='pbc',host=host,port=port)
        if DLCLIENT.is_alive():
            print("Connected")
            break
    except Exception as e:
        print(e)

def dl_put(bucketname, keyname, value, buckettype="default"):
    print("Creating key: " + keyname)
    print("  in bucket: " + bucketname)
    print("  of type: " + buckettype)
    bucket = DLCLIENT.bucket_type(buckettype).bucket(bucketname)
    obj = bucket.get(keyname)
    obj.encoded_data = value.encode()
    obj.store()

    time.sleep(1)
    # check if stored
    bucket2 = DLCLIENT.bucket_type(buckettype).bucket(bucketname)
    obj2 = bucket2.get(keyname)
    print("  with value: " + str(obj2.encoded_data.decode()))

bucketname = "__test__keyspace__;__test_bucket3__"
keyname = "__keyname3__"
buckettype = "default"
value = "__test_data3__"

dl_put(bucketname, keyname, value, buckettype)



# this is deprecated code
'''
client = RiakClient(protocol='pbc', nodes=[{'host':'172.17.0.2','http_port':8098,'pb_port':8087}])
#client.retries = 3

bucket = DLCLIENT.bucket_type('mfn_counter_trigger').bucket('counter_triggers')

# Use the code below when mapper wants to create a k-of-n parallel execution
# topic, key, value are separated by ";", and are used for trigger to publish <key, value> to kafka's topic.
# topic and key must not contain the character ";".  value can contain the character ";".
counter_name = 'topic;key;value'
k = 3
counter = bucket.new(counter_name)
counter.increment(k)
counter.store()

# Use the code below when a finishing parallel execution needs to decrease the counter by 1
# topic, key, value are separated by ";", and are used for trigger to publish <key, value> to kafka's topic.
# topic and key must not contain the character ";".  value can contain the character ";".
counter_name = 'topic;key;value'
counter = bucket.get(counter_name)
counter.decrement(1)
counter.store()

# Use the code below when reducer wants to delete the counter as the parallel execution has finished
# topic, key, value are separated by ";", and are used for trigger to publish <key, value> to kafka's topic.
# topic and key must not contain the character ";".  value can contain the character ";".
counter_name = 'topic;key;value'
bucket.delete(counter_name)

client.close()
'''