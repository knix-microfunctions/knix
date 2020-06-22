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

import math
import random
import time

MAX_RETRY = 1000
SLEEP_TIME = 1.0

def create_reducer_message(peg_id, job, num_mappers, final_next=None, mapper_id=None, next_reducer_id=None):
    # this is where the reducer is going to write its 'session function id'
    # i.e., running function id
    reducer_id_key = peg_id + "_reducer"

    message = {}
    message["peg_id"] = peg_id
    message["reducer_id_key"] = reducer_id_key
    message["num_mappers"] = num_mappers
    message["job"] = job
    if mapper_id is not None:
        message["mapper_id"] = mapper_id
    if next_reducer_id is not None:
        message["next_reducer_id"] = next_reducer_id
    if final_next is not None:
        message["final_next"] = final_next

    return message

def create_mapper_message_list(peg_id, job, data, num_mappers, reducer_id, mapper_conditions=None):
    # this assumes that num_mappers has been properly set before, so that
    # each mapper should get at least one item
    data_size = len(data)

    mapper_event_list = []
    data_size_per_mapper = int(math.ceil(data_size / num_mappers))
    for i in range(num_mappers):
        start = i * data_size_per_mapper
        end = (i+1) * data_size_per_mapper
        event = {}
        event["peg_id"] = peg_id
        event["mapper_id"] = i
        event["num_mappers"] = num_mappers
        event["reducer_id"] = reducer_id
        event["job"] = job
        event["data"] = data[start:end]
        if mapper_conditions is not None:
            event["mapper_conditions"] = mapper_conditions
        mapper_event_list.append(event)

    return mapper_event_list

def get_num_mappers_for_new_peg(data, num_mappers):
    data_size = len(data)

    # each mapper should get at least one item
    if data_size < num_mappers:
        num_mappers = data_size

    return num_mappers

def should_create_peg(data, mapper_conditions):
    # the criteria
    if mapper_conditions is not None:
        for cond in mapper_conditions:
            if cond == "max_len":
                if len(data) > mapper_conditions[cond]:
                    return True
    return False

def wordcount(data):
    words = []
    for line in data:
        words += line.split(" ")

    result = {}
    for word in words:
        if word == "":
            continue
        if word not in result:
            result[word] = 0
        result[word] += 1

    return result

def mergesort(data):
    # also cover longer inputs
    ret = None
    size = len(data)
    if size == 1:
        ret = data
    elif size == 2:
        ret = []
        if data[0] > data[1]:
            ret.append(data[1])
            ret.append(data[0])
        else:
            ret = data
    else:
        middle = int(size / 2)
        leftdata = data[:middle]
        rightdata = data[middle:]

        leftsorted = mergesort(leftdata)
        rightsorted = mergesort(rightdata)

        ret = []
        i = 0
        j = 0
        size1 = len(leftsorted)
        size2 = len(rightsorted)
        while i < size1 and j < size2:
            if leftsorted[i] < rightsorted[j]:
                ret.append(leftsorted[i])
                i += 1
            else:
                ret.append(rightsorted[j])
                j += 1

        while i < size1:
            ret.append(leftsorted[i])
            i += 1

        while j < size2:
            ret.append(rightsorted[j])
            j += 1

    return ret

def handle(event, context):
    # 1. check if we should create more dynamic PEGs
    # 2. if not:
    # 2.1 get reducer's info (i.e., storage key of where to find the running function id)
    # 2.2. process the data
    # 2.3. obtain the running function id of the reducer (i.e., look up the key from the data layer)
    # 2.4. use reducer's running function id to send it a message with the result
    # 3. if we should nest:
    # 3.1. create mappers and reducers
    # 3.2. pass the current reducer info to the newly generated reducer (so that it can also forward its result later)

    # 1. check whether we should create a nested dynamic PEG
    # if we generate another dynamic PEG, then we need to pass our
    # reducer id key to the just generated PEG's reducer
    my_data = event["data"]
    # 2.1. get reducer's info and obtain its corresponding key
    my_reducer_id = event["reducer_id"]
    my_id = event["mapper_id"]
    my_job = event["job"]
    my_num_mappers = event["num_mappers"]
    my_mapper_conditions = None
    if "mapper_conditions" in event:
        my_mapper_conditions = event["mapper_conditions"]

    should_nest = should_create_peg(my_data, my_mapper_conditions)

    if not should_nest:
        # 2.2. process the data
        if my_job["type"] == "wordcount":
            result = wordcount(my_data)
        elif my_job["type"] == "mergesort":
            result = mergesort(my_data)

        message = {}
        message["mapper_id"] = my_id
        message["mapper_result"] = result
        context.send_to_running_function_in_session(my_reducer_id, message, send_now=False)
    else:
        # 3.1. create additional mappers and reducer
        # pass the new reducer to the mappers
        # 3.2 pass the current reducer info to the reducer
        print("Going to create another PEG...")
        my_num_mappers = get_num_mappers_for_new_peg(my_data, my_num_mappers)

        random.seed()
        session_id = context.get_session_id()
        peg_id = session_id + "_" + str(time.time() * 1000.0) + "_" + str(random.uniform(0, 100000))

        # pass the current mapper_id, so that the original reducer will know we're done
        # also with our newly generated PEG
        # pass also the current reducer_id_key,
        # so that the newly generated reducer knows where to send the result (i.e., the original reducer of this mapper)
        reducer_message = create_reducer_message(peg_id, my_job, my_num_mappers, mapper_id=my_id, next_reducer_id=my_reducer_id)

        context.send_to_function_now("reducer", reducer_message)

        # 2.3. get the reducer's 'running function id' using the key
        retry = 0
        new_reducer_id = None
        new_reducer_key = reducer_message["reducer_id_key"]
        while retry < MAX_RETRY:
            new_reducer_id = context.get(new_reducer_key, is_private=True)
            if new_reducer_id is None or new_reducer_id == "":
                retry += 1
                #print("Could not find a proper running function id yet; retrying..." + str(retry) + " " + peg_id)
                time.sleep(SLEEP_TIME)
            else:
                break

        # 2.4. send result to the reducer via its running function id
        if new_reducer_id is None or new_reducer_id == "":
            print("ERROR: Could not create a new PEG. no proper running function id: " + new_reducer_key)
            raise "Could not create a new PEG: " + new_reducer_key

        mapper_message_list = create_mapper_message_list(peg_id, my_job, my_data, my_num_mappers, new_reducer_id, mapper_conditions=my_mapper_conditions)

        for msg in mapper_message_list:
            context.add_workflow_next("mapper", msg)

    return

