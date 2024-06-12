#!/usr/bin/python

def handle(event, context):
    context.log(str(event))

    #for it in event:
    #    it["summary"] = "test"

    return "This is a test summary!" 
    
