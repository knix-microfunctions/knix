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
import math
import random

def handle(event, context):
    # Generate a random number to determine whether the support case has been resolved, then return that value along with the updated message.
    min=0
    max=1
    myCaseStatus = math.floor(random.random() * (max - min + 1)) + min
    myCaseID = event['Case']
    myMessage = event['Message']
    if myCaseID == 1:
        # Support case has been resolved    
        myMessage = myMessage + "resolved..."
    elif myCaseStatus == 0:
        # Support case is still open
        myMessage = myMessage + "unresolved..."
    print("myCaseStatus: " +  str(myCaseStatus))
    result = {'Case': myCaseID, 'Status': myCaseStatus, 'Message': myMessage}    
    return result
    
