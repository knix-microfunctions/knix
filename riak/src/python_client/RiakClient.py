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

from riak import RiakClient

client = RiakClient(protocol='pbc', nodes=[{'host':'172.17.0.2','http_port':8098,'pb_port':8087}])
#client.retries = 3

bucket = client.bucket_type('mfn_counter_trigger').bucket('counter_triggers')

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
