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

import time

SLEEP_TIME = 1

def init(event, context):
    # 1. get reducer's info and obtain its corresponding key
    # do this first, so that we don't do processing if there is an error
    if "reducer_id_key" not in event:
        raise "Could not find corresponding reducer info."

    reducer_id_key = event["reducer_id_key"]
    rfid = context.get_session_function_id()
    context.put(reducer_id_key, rfid, is_private=True)

def cleanup(event, context):
    pass

def reduce_results_wordcount(mapper_results):
    final_result = {}
    for mapper in mapper_results:
        mapper_result = mapper_results[mapper]
        for word in mapper_result:
            if word not in final_result:
                final_result[word] = 0
            final_result[word] += mapper_result[word]

    return final_result

def reduce_results_mergesort(mapper_results):
    assert len(mapper_results) == 2
    data1 = mapper_results[0]
    data2 = mapper_results[1]

    ret = []
    i = 0
    j = 0
    size1 = len(data1)
    size2 = len(data2)
    while i < size1 and j < size2:
        if data1[i] < data2[j]:
            ret.append(data1[i])
            i += 1
        else:
            ret.append(data2[j])
            j += 1

    while i < size1:
        ret.append(data1[i])
        i += 1

    while j < size2:
        ret.append(data2[j])
        j += 1

    return ret

def handle(event, context):
    # 1. get reducer key and write running function id to it
    # 2. loop
    # 2.1. wait for messages
    # 2.2. process messages
    # 2.3. update and check conditions (e.g., k/n, k-list/n)
    # 3. post processing for 1) next and/or 2) further reducer
    # 4. send appropriate messages to 'next' and/or reducer

    # it can be the case that this reducer is for a dynamic parallel execution group (PEG),
    # which was generated inside a mapper (i.e., in another dynamic PEG).
    # in that case, this reducer might need to send a message to another reducer.
    # similar to what a regular mapper does:
    # 1. obtain the storage key for that reducer from the stack we get from the mapper
    # that generated us
    # 2. get its running function id
    # 3. send the result to it

    # it is also possible that the reducer might need to send a regular message
    # to some other function when exiting or executing (i.e., next)
    # this information needs to be available in the event

    # 1. get reducer key and write our running function id to it
    init(event, context)

    num_mappers_to_expect = event["num_mappers"]

    # initialize any other privately used data structures
    # for processing the incoming messages from other functions
    mapper_results = {}

    # 2. loop
    while context.is_still_running():
        #print("reducer: " + event["peg_id"] + ", result status: " + str(len(mapper_results)) + "/" + str(num_mappers_to_expect) + "; still looping...")
        # 2.1. get messages
        msgs = context.get_session_update_messages(count=num_mappers_to_expect)

        for msg in msgs:
            if msg != None:
                print("New message from mapper: " + str(msg)[:100] + " ...")
                # 2.2. process the message
                mapper_id = msg["mapper_id"]
                result = msg["mapper_result"]
                mapper_results[mapper_id] = result

        if len(mapper_results) == num_mappers_to_expect:
            print("All mapper results received; breaking the loop... " + event["peg_id"])
            break

        time.sleep(SLEEP_TIME)

    # 3. after the loop processing
    my_job = event["job"]
    if my_job["type"] == "wordcount":
        final_result = reduce_results_wordcount(mapper_results)
    elif my_job["type"] == "mergesort":
        final_result = reduce_results_mergesort(mapper_results)

    # 4. send the appropriate message
    if "next_reducer_id" in event and "mapper_id" in event:
        # get next reducer's info and send a message to it
        next_reducer_id = event["next_reducer_id"]
        my_id = event["mapper_id"]

        message = {}
        message["mapper_id"] = my_id
        message["mapper_result"] = final_result
        context.send_to_running_function_in_session(next_reducer_id, message, send_now=False)
    else:
        next_receiver = event["final_next"]
        context.add_workflow_next(next_receiver, final_result)

