import json

def handle(event, context):
    myCaseStatus = event['Status']
    myCaseID = event['Case']
    myMessage = event['Message'] + "closed."
    result = {'Case': myCaseID, 'Status' : myCaseStatus, 'Message': myMessage}
    return result

"""
exports.handler = (event, context, callback) => { 
    // Close the support case    
    var myCaseStatus = event.Status;    
    var myCaseID = event.Case;    
    var myMessage = event.Message + "closed.";    
    var result = {Case: myCaseID, Status : myCaseStatus, Message: myMessage};
    callback(null, result);
};
"""