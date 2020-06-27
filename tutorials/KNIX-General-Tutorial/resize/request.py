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

import base64, sys, json, requests, time

filename = sys.argv[1]  
print('sending ' + filename)
with open(filename, "rb") as image_file:
    encoded_file = base64.b64encode(image_file.read()).decode()

input_dict = {'Filename': filename, 'EncodedFile': encoded_file}
with open('request.json', 'w') as f:
    json.dump(input_dict, f)

# NOTE: This should be updated with the url of the deployed workflow
urlstr = 'https://wf-mfn1-1e6d6dbdf42466328ad9a216ca0fad82.mfn.knix.io:443'
t1=time.time()
r = requests.post(urlstr, json=input_dict, verify=False)
t2=time.time()
diff=(t2-t1)
print(diff, r.url, r.status_code, r.reason, r.text)
