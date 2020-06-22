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

import json, base64, io
from PIL import Image

# pre-requisite (PIL module should be downloaded in the current folder)
#   pip3 install pillow -t .
#         OR
#   docker run -it --rm -u $(id -u):$(id -g) -v $(pwd):/temp -w /temp python:3.6 pip3 install pillow -t .
# zip -r ../resize.zip .

def handle(event, context):
  filename = event['Filename']
  print('resize ' + filename)
  img = io.BytesIO(base64.b64decode(event['EncodedFile']))   # Read bytes from input

  with Image.open(img) as image:
    image.thumbnail(tuple(x/2 for x in image.size))          # Resize using PIL 
    buf = io.BytesIO()
    image.save(buf, format=image.format)                     # Store bytes in a buffer

    resized_name = filename+'_resize.jpg'
    if context != None:
      context.put(resized_name, base64.b64encode(buf.getvalue()).decode())  # Write buffer to KNIX key-value store
      print(resized_name + ' written to datalayer')
    else:
      with open(filename+'_resize.jpg', 'wb') as f:
        f.write(buf.getvalue())
      print(resized_name + ' written to local filesystem')

  event['Resized'] = filename+'_resize.jpg'                  # Return the name of the resize file
  event['EncodedFile'] = ''
  return event
