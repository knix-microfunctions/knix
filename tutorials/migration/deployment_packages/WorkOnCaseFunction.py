import json
import math
import random

def handle(event, context):
    min=0
    max=1
    myCaseStatus = math.floor(random.random() * (max - min + 1)) + min
    myCaseID = event['Case']
    myMessage = event['Message']
    if myCaseID == 1:
        # Support case has been resolved    
        myMessage = myMessage + "resolved..."
    elif myCaseStatus == 0:
        # Support case is still open
        myMessage = myMessage + "unresolved..."
    result = {'Case': myCaseID, 'Status' : myCaseStatus, 'Message': myMessage}    
    return result
    
"""
exports.handler = (event, context, callback) => {    
    // Generate a random number to determine whether the support case has been resolved, then return that value along with the updated message.
    var min = 0;
    var max = 1;    
    var myCaseStatus = Math.floor(Math.random() * (max - min + 1)) + min;
    var myCaseID = event.Case;
    var myMessage = event.Message;
    if (myCaseStatus == 1) {
        // Support case has been resolved    
        myMessage = myMessage + "resolved...";
    } else if (myCaseStatus == 0) {
        // Support case is still open
        myMessage = myMessage + "unresolved...";
    } 
    var result = {Case: myCaseID, Status : myCaseStatus, Message: myMessage};
    callback(null, result); 
};
"""