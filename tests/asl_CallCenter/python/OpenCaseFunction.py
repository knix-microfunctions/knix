import json

def handle(event, context):
    myCaseID = event['inputCaseID']
    myMessage = "Case " + myCaseID + ": opened..."
    result = {'Case': myCaseID, 'Message': myMessage}
    return result

"""
exports.handler = (event, context, callback) => {
    // Create a support case using the input as the case ID, then return a confirmation message   
   var myCaseID = event.inputCaseID;
   var myMessage = "Case " + myCaseID + ": opened...";   
   var result = {Case: myCaseID, Message: myMessage};
   callback(null, result);    
};
"""
