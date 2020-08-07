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

def handle(event, context):
    collector = {}
    #print("Log stream name:", context.log_stream_name)
    collector['log_stream_name'] = context.log_stream_name
    #print("Log group name:",  context.log_group_name)
    collector['log_group_name'] = context.log_group_name
    #print("Request ID:",context.aws_request_id)
    collector['aws_request_id'] = context.aws_request_id
    #print("Mem. limits(MB):", context.memory_limit_in_mb)
    collector['memory_limit_in_mb'] = context.memory_limit_in_mb
    print("Cognito Identity: ", context.identity)
    collector['context_identity'] = context.identity
    #print("Cognito Identity ID ", context.identity["cognito_identity_id"])
    #collector['cognito_identity_id'] = context.identity["cognito_identity_id"]
    #print("Cognito Identity Pool ID ", context.identity["cognito_identity_pool_id"])
    print("Client context ", context.client_context)
    collector['client_context']= context.client_context
    
    # Code will execute quickly, so we add a 1 second intentional delay so you can see that in time remaining value.
    #time.sleep(1) 
    #print("Time remaining (MS):", context.get_remaining_time_in_millis())
    collector['get_remaining_time_in_millis'] = context.get_remaining_time_in_millis()
    
    return collector
