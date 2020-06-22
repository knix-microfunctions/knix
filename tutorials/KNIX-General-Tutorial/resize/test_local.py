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

# Script for locally testing the resize function
# pre-requisite (PIL module should be downloaded in the current folder)
# docker run -it --rm -u $(id -u):$(id -g) -v $(pwd):/temp -w /temp python:3.6 pip3 install pillow -t .
#
# run as:
# docker run -it --rm -u $(id -u):$(id -g) -v $(pwd):/temp -w /temp python:3.6 python3 test_local.py

import json, base64

def test():
  import resize
  filename = 'leaves.jpg'
  with open(filename, "rb") as image_file:
      encoded_file = base64.b64encode(image_file.read()).decode()

  input_dict = {'Filename': filename, 'EncodedFile': encoded_file}

  print(str(resize.handle(input_dict, None)))

test()