<!--
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
-->
KNIX MicroFunctions Frequently Asked Questions (FAQ)
=====================================


1. What is serverless computing / function-as-a-service (FaaS)?
----------------------------------------------------------------
Serverless computing is emerging as a key paradigm in cloud computing. Unlike traditional approaches, which require developers to bundle applications as servers inside VMs or containers, in serverless computing or Function-as-a-Service (FaaS) developers write applications as sets of standalone functions. These Functions may be invoked via HTTP requests or triggered by other internal or external events. Developers do not need to manage servers or provision server capacity in advance because all aspects related to function execution, placement, scaling, etc., are handled by the serverless platform.

2. What is KNIX MicroFunctions?
----------------
KNIX MicroFunctions is a high-performance serverless computing platform.

3. How is KNIX MicroFunctions better?
----------------------
KNIX MicroFunctions reduces the latency of function interactions for applications as well as increases the resource efficiency for platform operators.

4. How does it work?
--------------------
KNIX MicroFunctions employs two key ideas: 1) It groups functions of the same application together in the same container as separate processes, and 2) It utilizes a hierarchical message bus and data layer to support fast function interactions.

The first idea enables KNIX MicroFunctions to invoke function executions much faster than starting new containers or VMs as well as to be more resource efficient. The second idea further reduces the interaction latency by exploiting locality of functions belonging to the same application.

For more details, please refer to our paper published in USENIX ATC 2018 (<https://www.usenix.org/system/files/conference/atc18/atc18-akkus.pdf>).

5. Do I have to manage the servers that run my application?
------------------------------------------------------------------
No. As a developer, you should not be concerned about managing the servers that run your application in KNIX MicroFunctions.

6. Do I need to monitor the load of my application and make scaling decisions?
------------------------------------------------------------------------------
No. KNIX MicroFunctions will do that for you.

7. Which languages are supported?
---------------------------------
KNIX MicroFunctions currently supports Python 3.6 and Java 8. Support for other languages (JavaScript (with node.js) and C/C++) is under development.

8. What are functions and workflows?
---------------------------------
In KNIX MicroFunctions, a function of an application is called a function, and the function's code is called function code. Each function code must define a method named 'handle' which is the default entry for that function. This 'handle' method is invoked by the KNIX MicroFunctions platform when an invocation for that function arrives.

An application consists of one or more functions that can be grouped as one or multiple workflows. Workflows define the interactions among these functions. Workflows can be static, where the execution path of functions is fixed (e.g., Function 2's execution always follows Function 1's execution), or dynamic, where the execution path is determined during the execution (e.g., the execution of Function 2 may be programmatically triggered by Function 1's code). The function code and a workflow description are supplied by the application developer. A function can be used by multiple applications by referencing it in different workflows.

If a function's execution fails for some reason then the subsequent functions (either statically defined or dynamically defined) will not be executed.

9. What are sandboxes, function workers and function instances?
---------------------------------------------------------
An application runs inside a Docker container hosted on a server machine.  The container is referred to as the 'sandbox' and server as the 'host'. By default all functions belonging to an application run inside a single sandbox. A developer may choose to split their application into multiple smaller applications, each containing a subset of functions and running inside a separate sandbox. These sandboxes may be scheduled on different hosts by the KNIX MicroFunctions platform.

A function inside a sandbox runs as a dedicated OS process called function worker.  The function worker loads the associated function code and its dependencies,  subscribes to the event queue, and waits for events - which are invocations for the function associated with the function. Upon receiving an event, the function worker forks itself (using OS's fork() command) to create a function instance that handles the event. The function instance executes the function code and terminates imediately after the execution.

For more details, please see our paper published in USENIX ATC 2018 (https://www.usenix.org/system/files/conference/atc18/atc18-akkus.pdf). Please feel free to contact the KNIX MicroFunctions team if you have more questions.

10. How do I handle state for my application?
---------------------------------------------
KNIX MicroFunctions provides a built-in key-value store which is shared between all functions created by a user account. This key-value store can be accessed by the function code via the MicroFunctions API object. This API object is passed as the input parameter, 'context', to the function's 'handle' method.

This built-in key-value store could be used to persist any data associated with a single function or to share data between functions. KNIX MicroFunctions utilizes its hierarchical data layer to enable fast function interactions, such that sharing data between different functions should not affect the performance of an application. Any other network-accessible storage service can also be used by KNIX MicroFunctions functions. Accesses to these external storage services do not  benefit from KNIX MicroFunctions's hierarchical data layer.

11. What are the properties of the key-value store and its API?
---------------------------------------------------------------
The keys and values used in the put, get, and delete operations must be strings.

By default, the items will be written into the data layer of the user, so that the items produced by one workflow will be accessible by another workflow that belongs to the same user. Sharing across users is currently not supported.

Additionally, one can use another parameter (i.e., `is_private = True`) in all these operations to access a workflow-private key-value store, so that the items will only be accessible to the corresponding workflow.

By default, all items put and deleted from the key-value store are immediately made available in the global data layer without waiting for the function execution to finish. One can set another parameter (`is_queued = True`) to postpone the operation to the global data layer, so that it will only happen if the function execution successfully finishes. By default all items available in the global data layer can be accessed via any function defined by the same user. Access to data items can also be limited to functions belonging to a single workflow.

These concepts are illustrated in the following sample invocations to the `put` API:

`context.put('mykey', 'myvalue')`: `mykey` will be available to all workflows of the user, and will also be made available immediately in the global data layer.

`context.put('mykey', 'myvalue', is_private = True)`: `mykey` will be available only to this workflow's functions, and will also be made available immediately in the global data layer.

`context.put('mykey', 'myvalue', is_queued = True)`: `mykey` will be available to all workflows of the user, and will be made available in the global data layer after the function execution successfully finishes.

`context.put('mykey', 'myvalue', is_private = True, is_queued = True)`: `mykey` will be available only to this workflow's functions, and will be made available in the global data layer after the function execution successfully finishes.

12. What other functions does the MicroFunctions API object support?
----------------------------------------------------------
1. add_dynamic_next(next_function, value)
Used to dynamically (or programmatically) define the next function to be invoked. 'next_function' is the name of the next function to be invoked and the 'value' in the input value passed to that function.
Note: the name of the dynamically invoked function must be listed in the 'potentialNext' field (in the workflow description) of the function invoking the 'add_dynamic_next' API.

2. log(string)
Used to add log statements to the workflow logs. The workflow logs are made available via the GUI. Any errors in function executions are also recorded in the workflow log.
KNIX MicroFunctions also supports regular 'print' statements, which are also recorded in the workflow log.

13. How do I create a function?
----------------------------
In the KNIX MicroFunctions GUI, click on the 'Functions' link shown on the left hand side. This will open up a page listing all the functions created by the current user. Add a new function by pressing the 'Add Function' button and giving it a name. A code editor window will open up automatically. Write the function code in the editor and press 'Save'. Alternatively, function code can be written offline and uploaded using the code editor. To upload function code, click the 'Upload' tab and browse to the file containing the code. This file will be uploaded as the function code which will become available in the editor after uploading finishes.

14. What is the input to a function?
---------------------------------
There are two input parameters to the `handle()` function of each function.

1. `event`: This is the string input value to the function. The function code is responsible for interpreting/parsing this input string correctly. For example, if an object is passed to the function as a JSON encoded string, then the function code should decode it before using it.

2. `context`: This is the MicroFunctions API object, which exposes APIs for KNIX MicroFunctions's key-value store, logging, and dynamic invocation of functions (see questions 11 and 12).

15. How do I test a function?
--------------------------
Individual functions can be tested by clicking the 'Test' button next to the function. This will open a window where the function can be executed with a user provided string input. The bottom half of the window shows the function's return value and logs generated by the function.

16. How can I create a function with custom libraries?
---------------------------------------------------
Dependencies that are not part of the standard Python distribution, such as those that can be installed via 'pip install' or your own custom packages, can easily be included with your function code by creating a deployment package for the function. To create this package, first store the function code in a local folder. Next, copy all dependencies to this folder next to the function code. For example, you can use `pip install <package name> -t .` to install a Python package directly into this folder. Afterwards, zip the contents of this folder via `zip -r ../<functionname>.zip .` command. This zip file is the deployment package for the function.
Next, create a function and upload the zip file using the 'Upload' tab. KNIX MicroFunctions will automatically extract the contents of the zip file and display it after uploading has finished. Afterwards, you may view/modify your function code using the function code editor. Any updates made to the code will be used when deploying a workflow involving this function. Note that your function code's filename (i.e., `<functionname>.py`) must match the function name you create in the GUI (i.e., `<functionname>`).

KNIX MicroFunctions currently supports only zip/jar archives. Other archive formats (e.g., tar) will be supported in the future.

Alternatively, if your function only requires packages that are pip-installable, they can be listed in the 'Requirements' tab of the function code editor window. Required functions for Java functions can be specified in the format of a Maven pom.xml file.

17. How do I create a workflow?
-------------------------------
In the GUI, you will see a link on the left hand side, named 'Workflows'. This page lists all the workflows you have created so far as well as their status (i.e., deployed/undeployed) and their publicly accessible address to trigger them via a web browser or command line tools (such as curl and wget). KNIX MicroFunctions workflows use are JSON-encoded using Amazon's States Language (ASL) specification. When you add a workflow description, you will be presented with a template. You can find more info about ASL here: <https://states-language.net/spec.html>

18. How do I redeploy a modified version of my workflow?
--------------------------------------------------------
You need to undeploy the modified workflow and redeploy it. Note that any function code changes also require a re-deployment of the associated workflow (except for testing individual functions). The workflow editor provides a button 'Redeploy and execute' to simplify this step.

20. Do you support versioning of functions or workflows?
-----------------------------------------------------
There is currently no versioning support of functions and workflows. That means only the most recent version of the function code or workflow description are stored by the KNIX MicroFunctions platform. We are planning to support versioning in the future.

24. I have an AWS Step Functions state machine file. Can I run it on KNIX MicroFunctions?
--------------------------------------------------------------------------
Yes, KNIX MicroFunctions supports the Amazon States Language (ASL) specifiction used to define a step function state machine in addition to its own workflow definition language. You can copy your ASL specification into the KNIX MicroFunctions workflow JSON editor and just need to ensure that each 'Resource' field in your specification is assigned to the name of a function in your KNIX MicroFunctions account (instead of an AWS Lambda function identifier).

25. Do you support environment variables for my application's sandbox?
----------------------------------------------------------------------
Yes, you can set them in your Python code as in the example below. We will also soon add the ability to set environment variables through the web GUI.

```
#!/usr/bin/python
import os

def handle(event, context):
    os.environ['MY_ENV_VARIABLE] = 'myValue'    
    return event
```
