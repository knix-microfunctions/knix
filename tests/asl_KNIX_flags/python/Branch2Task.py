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
def print_dict(event):
	if isinstance(event, dict):
		for key,value in event.items():
			print((key + ":" + str(value)))
	else:
		print('[print_dict] Input is not a dict')

def handle(event, context):
	name = 'Branch2Task.py'
	int_add = 20
	float_add = 20.0
	print('Hello from ' + name)
	print(type(event))
	#time.sleep(5)
	if type(event) == type({}):
		print_dict(event)
		event['functionName'] = name
		return event
	elif type(event) == type(''):
		print(event)
		event = event +  ' ' + name
		return event
	elif type(event) == type([]):
		print(event)
		event = event + [name]
		return event
	elif type(event) == type(5):
		print(event)
		event = event + int_add
		return event
	elif type(event) == type(1.0):
		print(event)
		event = event + float_add
		return event
	else:
		print(event)
		return event

