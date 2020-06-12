import json

def handle(event, context):
    myCaseID = event['Case']
    myMessage = event['Message'] + "assigned..."
    result = {'Case': myCaseID, 'Message': myMessage}
    return result

"""
exports.handler = (event, context, callback) => {    
    // Assign the support case and update the status message    
    var myCaseID = event.Case;    
    var myMessage = event.Message + "assigned...";    
    var result = {Case: myCaseID, Message: myMessage};
    callback(null, result);        
};
"""