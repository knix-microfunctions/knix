#!/usr/bin/python

def handle(event, context):
    event["payment"] = "Ok"
    return event

