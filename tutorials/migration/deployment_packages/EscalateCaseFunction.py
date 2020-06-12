import json

def handle(event, context):
    myCaseID = event['Case']
    myCaseStatus = event['Status']
    myMessage = event['Message'] + "escalating."
    result = {'Case': myCaseID, 'Status' : myCaseStatus, 'Message': myMessage}
    return result
    
"""
exports.handler = (event, context, callback) => {    
    // Escalate the support case 
    var myCaseID = event.Case;    
    var myCaseStatus = event.Status;    
    var myMessage = event.Message + "escalating.";    
    var result = {Case: myCaseID, Status : myCaseStatus, Message: myMessage};
    callback(null, result);
};
"""