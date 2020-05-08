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

{
  "prod": "R31",
  "dest-code": 9511,
  "quantity": 1344
}
"""

def handle(event, context):
    #if "parcel" in event.keys():
    #    keys = event["parcel"].keys()

        keys = event.keys()

        if "prod" in keys and "dest-code" in keys and "quantity" in keys: 
           retP = "parcel OK"
        else:
           retP = "parcel NOK"
    #if "courier" in event.keys():
    #    retC = "courier OK"
    #else:
    #    retC = "courier NOK"
        
    #return {"parcel": retP, "courier": retC}
        return {"parcel": retP}
    
