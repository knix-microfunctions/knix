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
import requests

#proxies = {"https":"http://192.168.0.1:3128/"}

def retrieve_news(key, source):

    url = "https://newsapi.org/v2/top-headlines?sources=%s&apiKey=%s" %  (source, key)

#    response = requests.get(url, proxies = proxies)
    response = requests.get(url)

    #print(response.json())
    #return response.json()
    return json.loads(response.text.encode('ascii', 'ignore'))


# What AWS Lambda calls
def handle(event, context):

    #key = os.getenv('NEWSAPI_KEY')

    key = event['key']

    if not key:
        raise Exception('Not all environment variables set')

    if not event['source']:
        raise Exception('Source not set')

    return {'data': retrieve_news(key, event['source']),
            'source': event['source']}


