#!/usr/bin/python
"""
{
  "parcel": {
    "prod": "R31",
    "dest-code": 9511,
    "quantity": 1344
   },
   "courier": "UQS"
}
"""

def handle(event, context):
    
    ret = "item NOK!"
    if ("courier" in event and "parcel" in event): # just check for the keys
       ret = "item OK!"
       par = event["parcel"]
       if "prod" in par.keys() and "dest-code" in par.keys() and "quantity" in par.keys():
           ret = "All keys are OK!"
    
    return ret
	
