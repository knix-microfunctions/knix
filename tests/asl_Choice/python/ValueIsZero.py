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

import json
import time

def print_dict(event, context):
        if isinstance(event, dict):
                for key,value in event.items():
                        print((key + ":" + str(value)))
        else:
                print('[print_dict] Input is not a dict')

def handle(event, context):
        name = "ValueIsZero.py"
        print(('Hello from ' + name))
        

        print(type(event))
        if type(event) == type({}):
                event['functionName'] = name
                print_dict(event, context)
                return event
        else:
                print(event) 
                return event

