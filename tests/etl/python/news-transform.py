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

import sys
import csv
from io import BytesIO, StringIO
 
# What AWS Lambda calls
def handle(event, context):

    if sys.version_info < (3, 0):
        sio = BytesIO()
    else:
        sio = StringIO()

    writer = csv.writer(sio)
    writer.writerow(["Source", "Title", "Author", "URL"])
    for article in event['data']['articles']:
        writer.writerow([
            article['source']['name'],
            article['title'],
            article['author'],
            article['url']
        ])
 
    csv_content = sio.getvalue()
    print(csv_content)
 
    return {'data': csv_content,
            'source': event['source']}


