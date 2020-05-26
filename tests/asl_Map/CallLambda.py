import json
import time
def handle(event, context):
    name = event["who"]
    time.sleep(1.0)
    return "Hello, %s!" % name 
