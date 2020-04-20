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

def handle(event, context):
    name = 'FailFunction.py'
    print('Hello from ' + name)
    print(type(event))
    
    if "invalid_value" in event:
        raise ValueError(name + " does not like this value!")
    elif "invalid_type" in event:
        raise TypeError(name + " does not like this type!")
    elif "invalid_denominator" in event:
        raise ZeroDivisionError(name + " does not like this value!")
    else:
        raise Exception("States.All")
    
    return event

