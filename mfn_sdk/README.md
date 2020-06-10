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
# KNIX MicroFunctions SDK

Easy-to use package to access the management interface of KNIX MicroFunctions as well as
deployed workflows.

The latest version of the SDK can be obtained from [KNIX releases](https://github.com/knix-microfunctions/knix/releases/).
It is also hosted at PyPI and can be installed with the PyPA recommended tool for installing Python packages:
``` sh
pip3 install mfn_sdk
```

## Setup the client

The MFN client can be configured by various means, using precedence of the following order:
* configuration file `../settings.json`, `~/settings.json` and/or `./settings.json`)
* environment variables (`MFN_URL`, `MFN_USER`, `MFN_PASSWORD`, `MFN_NAME`)
* using the constructor `MfnClient(mfn_url,mfn_user,mfn_password,mfn_name,proxies)`

The configuration file should contain a JSON dictionary with the parameter names as keys:

``` json
{
    "mfn_url": "<http://host:port>",
    "mfn_user": "<email>",
    "mfn_password": "<password>",
    "mfn_name": "<full name>",
    "proxies":
    {
        "http": "http://<proxyhost>:<port>",
        "https": "http://<proxyhost>:<port>"
    }
}
```

An equivalent of environment variables can also be used, with the exception of the proxy configuration, which uses the `http_proxy` and `https_proxy` variables:
``` sh
export MFN_URL="<http://host:port>"
export MFN_USER="<email>"
export MFN_PASSWORD="<password>"
export MFN_NAME="<full name>"
export HTTP_PROXY="http://<proxyhost>:<port>" # or http_proxy
export HTTPS_PROXY="http://<proxyhost>:<port>" # or https_proxy
```

To overwrite parameters at runtime, they can be passed in the constructor.
``` py
from mfn_sdk import MfnClient

# MfnClient(mfn_url,mfn_user,mfn_password,mfn_name,proxies)
mfn = MfnClient(
    mfn_url="<http://host:port>",
    mfn_user="<email>",
    mfn_password="<password>",
    mfn_name="<full name>",
    proxies={
        "http": "http://<proxyhost>:<port>",
        "https": "http://<proxyhost>:<port>"
    })
```

NOTE: The `mfn_name` parameter is only used if the user does not exist (as it is required for every new user). If the parameter is missing, the client SDK will only try to login but won't create a user.

## List functions and workflows

``` py
from mfn_sdk import MfnClient
mfn = MfnClient(
    mfn_url="https://knix.io/mfn",
    mfn_user="test@example.com",
    mfn_password="test123",
    mfn_name="Mr. Test")

for function in mfn.functions:
    print(function)

for workflow in mfn.workflows:
    print(workflow)
```

## Create a new workflow

To create a simple workflow with just a single function, the function source and the workflow description is required.
A function can have plaintext code or a ZIP file or both attached to it (more below).

``` py
function = mfn.add_function("echo")
function.code = """
def handle(event, context):
    context.log("Echoing"+event)
    return event
"""
```

The associated workflow description is provided as a string containing the JSON.

``` py
wf = mfn.add_workflow('wf_echo')
wf.json = """{
  "Comment": "Echo workflow",
  "StartAt": "entry",
  "States": {
    "entry": {
      "Type": "Task",
      "Resource": "echo",
      "End": true
    }
  }
}"""
```

## Read and write objects (Note: only strings are allowed)

The key-value storage shared by workflows of a tenant can be modified or accessed using put(), get() and delete() on the client object:

```py
mfn.put("my_key","some-value")
print("We have stored: " + mfn.get("my_key"))
mfn.delete("my_key")
mfn.keys() # should be empty list
```

## Function ZIPs

A function can be a source code string and/or a ZIP file. If the ZIP file contains a source file with the name of the resource (i.e., function name), then its handle function would be used as a starting point.
However, if source code is also attached as a string, it would overwrite said file and be used instead.

In the following example, the current directory is zipped and uploaded as a function ZIP.

``` py
import os
from zipfile import ZipFile
# Create a new function
g = mfn.add_function('myfunction')

# Create a zip file from the directory contents
zip_name = "myfunction.zip"
if os.path.exists(zip_name):
    os.remove(zip_name)

for root,dirs,files in os.walk('.'):
    with ZipFile(zip_name,'w') as zf:
        for fn in files:
            zf.write(fn)

# upload the zip file
g.upload(zip_name)
```

## Execute workflows

Once a workflow has been created and its functions have been uploaded, it can be deployed and executed using the client SDK.
The `deploy(timeout=None)` function can use a timeout. If `timeout=None`, it will immediately return after requesting deployment. If `timeout=0`, it will wait indefinitely for the workflow to change its status to "deployed". Any `timeout > 0` will wait for that many seconds and throw an exception if the workflow hasn't reached the status "deployed" by then.

The `execute(data,timeout=60)` function invokes a deployed workflow. Here, timeout is passed to the Python requests HTTP transaction that invokes the workflow execution.

Using the above echo workflow example, we have created an `echo_wf` workflow object, which can be deployed and executed as follows:
``` py

wf.deploy(timeout=0) # wait until wf.status=='deployed'
print("Sending Hello")
result = wf.execute("Hello")
print(f"Received {result}")

```
