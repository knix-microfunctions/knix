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

#!/usr/bin/python

import time, datetime

def handle(event, context):
    c = {}
    print (context.function_name)
    c['context.function_name'] = context.function_name
    print (context.function_version)
    c['context.function_version'] = context.function_version
    
    print (context.log_stream_name)
    c['context.log_stream_name'] = context.log_stream_name
    print (context.log_group_name)
    c['context.log_groupm_name'] = context.log_group_name
    print (context.aws_request_id)
    c['context.aws_request_id'] = context.aws_request_id
    print (context.memory_limit_in_mb)
    c['context.memory_limit_in_mb'] = context.memory_limit_in_mb
    

    #print (str(context.identity))
    #c['context.identity'] = str(context.identity)
    print (context.identity.cognito_identity_id)
    c['context.identity.cognito_identity_id'] = context.identity.cognito_identity_id
    print (context.identity.cognito_identity_pool_id)
    c['context.identity.cognito_identity_pool_id'] = context.identity.cognito_identity_pool_id

    #print (str(context.client_context))
    #c['context.client_context'] = str(context.client_context)
    print (str(context.client_context.client))
    c['context.client_context.client'] = str(context.client_context.client)
    print (str(context.client_context.custom))
    c['context.client_context.custom'] = str(context.client_context.custom)
    print (str(context.client_context.env))
    c['context.client_context.env'] = str(context.client_context.env)

    print (context.client_context.client.installation_id)
    c['context.client_context.client.installation_id'] = context.client_context.client.installation_id
    print (context.client_context.client.app_title)
    c['context.client_context.client.app_title'] = context.client_context.client.app_title
    print (context.client_context.client.app_version_name)
    c['context.client_context.client.app_version_name'] = context.client_context.client.app_version_name
    print (context.client_context.client.app_version_code)
    c['context.client_context.client.app_version_code'] = context.client_context.client.app_version_code
    print (context.client_context.client.app_package_name)
    c['context.client_context.client.app_package_name'] = context.client_context.client.app_package_name
    print (context.get_remaining_time_in_millis())
    c['context.get_remaining_time_in_millis'] = context.get_remaining_time_in_millis()
    return c
