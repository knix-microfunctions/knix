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

"""
  zip: a script that exemplifies the upload of a function's custom ZIP file
"""
import requests
import os
import base64
import sys
import datetime

from zipfile import ZipFile
from mfn_sdk import MfnClient

import logging
logging.basicConfig(level=logging.DEBUG)

c = MfnClient(
        'https://knix.io',
        'test@test.com',
        'test123',
        proxies={})


"""
This example uploads a given ZIP file to a function
"""

# Create a new function
g = c.add_function('custom')

# Create a zip file from the directory contents
zip_name = "custom_function.zip"
if os.path.exists(zip_name):
    os.remove(zip_name)
for root,dirs,files in os.walk('.'):
    with ZipFile(zip_name,'w') as zf:
        for fn in files:
            zf.write(fn)

# upload the zip file
g.upload(zip_name)



"""
Uploading the zip file is a combination of uploading 1MB file chunks and metadata that includes the zip archive listing.
The process can be customized (e.g. archive listing), below is a manual version of chunking and uploading the function ZIP file.
"""

# load the zip file as 1MB chunks
chunks=[]
with open(zip_name, 'rb') as zf:
    for chunk in iter(lambda:zf.read(1024*1024), ''):
        chunks.append(base64.b64encode(chunk))

# create metadata information on the ZIP file contents
metadata = "Last uploaded Zip file: <b>" + zip_name + "</b><br><br><table border='1'>"
with ZipFile(zip_name, 'r') as zf:
    for fn in zf.namelist():
        try:
            fi = zf.getinfo(fn)
        except KeyError:
            print('ERROR: Did not find %s in zip file' % fn)
        else:
            metadata += "<tr>" \
                "<td style='padding: 5px 5px 5px 5px;'>%s</td>" \
                "<td style='padding: 5px 5px 5px 5px;'>%.2f kB</td>" \
                "<td style='padding: 5px 5px 5px 5px;'>%s</td>" \
                "</tr>" % (fn, fi.file_size/1024.0, datetime.datetime(*fi.date_time))
metadata += "</table>"

# upload the zip file
source = {'zip':chunks,'metadata':base64.b64encode(metadata)}
g.source = source
