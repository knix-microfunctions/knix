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

def preprocess_data(data, job):
    if job["type"] == "wordcount":
        if job["input_format"] == "string":
            data = data.split("\n")
        elif job["input_format"] == "array":
            pass

    return data

def handle(event, context):

    # 1. create reducer's info and trigger reducer
    # 2. create mapper data partitions and trigger mappers

    # reducer info:
    # 1. reducer id storage key
    # 2. conditions (e.g., k/n, k-list/n)

    # mapper info:
    # 1. reducer id storage key
    # 2. mapper data

    #print(event)

    job = event["job"]
    data = event["data"]
    num_mappers = event["num_mappers"]
    # ensure the num_mappers is in a valid range
    num_mappers = get_num_mappers_for_new_peg(data, num_mappers)

    mapper_conditions = None
    if "mapper_conditions" in event:
        mapper_conditions = event["mapper_conditions"]

    random.seed()
    session_id = context.get_session_id()
    peg_id = session_id + "_" + str(time.time() * 1000.0) + "_" + str(random.uniform(0, 100000))

    # TODO: any other jobs and their characteristic
    # input formats and preprocessing steps
    data = preprocess_data(data, job)

    reducer_message = create_reducer_message(peg_id, job, num_mappers, final_next="final")

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

    mapper_message_list = create_mapper_message_list(peg_id, job, data, num_mappers, new_reducer_id, mapper_conditions=mapper_conditions)

    for msg in mapper_message_list:
        context.add_workflow_next("mapper", msg)

    return

