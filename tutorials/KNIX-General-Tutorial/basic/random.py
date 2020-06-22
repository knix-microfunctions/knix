#!/usr/bin/python
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

import numpy as np
def handle(event, context):
    a = np.random.normal(size=event)
    b = a.tolist()
    print(str(b))
    return b

# curl --header "Content-Type: application/json" --request POST --data '3' https://wf-mfn1-d46cebff37bcbb273c86d605b8acc278.mfn.knix.io:443