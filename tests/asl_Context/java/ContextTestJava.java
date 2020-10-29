/*
   Copyright 2020 The KNIX Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import org.json.JSONObject;
import org.microfunctions.mfnapi.MicroFunctionsAPI;

public class ContextTestJava
{
    public Object handle(Object event, MicroFunctionsAPI context)
    {
        JSONObject testResultMap = new JSONObject();

        testResultMap.put("context.function_name", context.getFunctionName());
        testResultMap.put("context.function_version", context.getFunctionVersion());
        testResultMap.put("context.log_stream_name", context.getLogStreamName());
        testResultMap.put("context.log_group_name", context.getLogGroupName());
        testResultMap.put("context.aws_request_id", context.getAwsRequestId());
        testResultMap.put("context.memory_limit_in_mb", context.getMemoryLimitInMB());
        testResultMap.put("context.invoked_function_arn", context.getInvokedFunctionArn());
        
        testResultMap.put("context.identity", context.getIdentity());
        //testResultMap.put("context.identity.cognito_identity_id", context.getIdentity().cognitoIdentityId);
        //testResultMap.put("context.identity.cognito_identity_pool_id", context.getIdentity().cognitoIdentityPoolId);
        
        testResultMap.put("context.client_context.client", context.getClientContext());
        //testResultMap.put("context.client_context.custom", context.getClientContext().custom);
        //testResultMap.put("context.client_context.env", context.getClientContext().env);
        //testResultMap.put("context.client_context.client.installation_id", context.getClientContext().client.installationId);
        //testResultMap.put("context.client_context.client.app_title", context.getClientContext().client.appTitle);
        //testResultMap.put("context.client_context.client.app_version_name", context.getClientContext().client.appVersionName);
        //testResultMap.put("context.client_context.client.app_version_code", context.getClientContext().client.appVersionCode);
        //testResultMap.put("context.client_context.client.app_package_name", context.getClientContext().client.appPackageName);

        testResultMap.put("context.get_remaining_time_in_millis", context.getRemainingTimeInMillis());
        return testResultMap;
    }
}
