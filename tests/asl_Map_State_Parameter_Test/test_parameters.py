import json
from ujsonpath import parse

input = [{"who": "bob"},{"who": "meg"},{"who": "joe"}]

parameters = {
              "ContextIndex.$": "$$.Map.Item.Index",
              "ContextValue.$": "$$.Map.Item.Value",    
             } 

expected_response = [{"ContextValue": {"who": "bob"}, "ContextIndex": 0},{"ContextValue": {"who": "meg"}, "ContextIndex": 1}, {"ContextValue": {"who": "joe"}, "ContextIndex": 2 }]

"""
input = [{"comment": "Example for Parameters.",
  "product": {
    "details": {
       "color": "blue",
       "size": "small",
       "material": "cotton"
    },
    "availability": "in stock",
    "sku": "2317",
    "cost": "$23"
  }
}]

parameters = {"comment": "Selecting what I care about.",
  "MyDetails": {
      "size": "small",
      "exists": "in stock",
      "StaticValue": "foo"
  }
}

expected_response = {
  "comment": "Selecting what I care about.",
  "MyDetails": {
      "size": "small",
      "exists": "in stock",
      "StaticValue": "foo"
  }
}

input = {"delivery-partner": "UQS", "shipped": {
 "prod": "R31",
 "dest-code": 9511,
 "quantity": 1344}}

input = {
    "delivery-partner": "UQS",
    "shipped": 
[
      { "prod": "R31", "dest-code": 9511, "quantity": 1344 },
      { "prod": "S39", "dest-code": 9511, "quantity": 40 },
      { "prod": "R31", "dest-code": 9833, "quantity": 12 },
      { "prod": "R40", "dest-code": 9860, "quantity": 887 },
      { "prod": "R40", "dest-code": 9511, "quantity": 1220 }
    ]
  }

parameters = {"parcel.$": "$$.Map.Item.Value", "courier.$": "$.delivery-partner" }

expected_response =  { "parcel": {
 "prod": "R31",
 "dest-code": 9511,
 "quantity": 1344},
 "courier": "UQS"
}

"""

def process_parameters(parameters, state_data):
        ret_value = None
        ret_item_value = None
        ret_item_index = None

        print ("state data input: " + str(state_data))

        if parameters == "$": # return unfiltered input data
            ret_value = state_data
        elif parameters is None: #return empty json
            ret_value =  {} 
        else: # contains a parameter filter, get it and return selected kv pairs
            ret_value = {} 
            ret_index = {}
            for key in parameters.keys():
                #print(key)
                if key.casefold() == "comment".casefold(): # ignore
                    ret_value[key] = parameters[key]
               
                elif parameters[key] == "$$.Map.Item.Value": # get Items key 
                       value_key = key.split(".$")[0]
                       ret_value = value_key
                       ret_item_value = value_key

                elif parameters[key] == "$$.Map.Item.Index": # get Index key
                       index_key = key.split(".$")[0]
                       ret_index = index_key
                       ret_item_index = index_key
                else:
                     #print(parameters[key])
                     if isinstance(parameters[key], dict): # parameters key refers to dict 
                        print("Hello dict")
                        ret_value[key] = {}
                        for k in parameters[key]: # get nested keys
                           print(k)
                           if not k.split(".")[-1] == "$": # parse static value
                               #print (parameters[key][k])
                               ret_value[key][k] = parameters[key][k]
                           else:
                               #print(state_data, parameters[key][k])
                               new_key = k.split(".$")[0] # use the json paths in paramters to match 
                               ret_value[key][new_key] = [match.value for match in parse(parameters[key][k]).find(state_data)][0]
                        return ret_value
                     if isinstance(parameters[key], str): # parameters ky refers to string
                        print("hello str")
                        ret_value = {}
                        new_key = key.split(".$")[0] # get the parameters key
                        query_key = parameters[key].split("$.")[1] # correct the correspondig value
                        new_value = state_data[query_key] # save the actual value before replacing the key

                        #state_data = state_data["shipped"] # simulate ItemsPath filter 
                        for kk in state_data.keys():

                         if isinstance(state_data[kk], dict): 
                            print ("hello dict") 
                            ret_value[new_key] = new_value
                            if ret_item_value != None:
                                 ret_value[ret_item_value] = state_data[kk]
                            else:
                                 raise Exception("Error: item value is not set!")
                            ret_value_dict = {}
                            ret_value_dict[kk] = ret_value
                            return ret_value_dict

                         if isinstance(state_data[kk], list): 
                            print("Hello list")
                            ret_value_list = [] 
                            for data in state_data[kk]:
                                #ret_value[new_key] =  new_value
                                #if ret_item_value != None:
                                #    ret_value[ret_item_value] = data
                                ret_value_list.append({new_key: new_value, ret_item_value: data})
                                #else:
                                #    raise Exception("Error: item value is not set!")
                            ret_value_dict = {}
                            ret_value_dict[kk] = ret_value_list 
                            return ret_value_dict
                     else:
                        raise Exception("Error: invaldid Parmeters format: " + str(parameters[key]))
 
        ret_total = []
        print ("hello All")
         
        for key  in state_data:
            if ret_value != {} and ret_index == {}:
                ret_total.append({ret_value: key})
            elif ret_value == {} and ret_index != {}:
                ret_total.append({ret_index: state_data.index(key) })
            elif ret_value != {} and ret_index != {}:
                ret_total.append({ret_value: key, ret_index: state_data.index(key) })
            else:
                raise Exception("Unknown Map State parse error")
        ret_value = ret_total
        return ret_value

#print (process_parameters(parameters, input) == expected_response )
print (process_parameters(parameters, input) )

