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
# MicroFunctions Command Line Interface

The package provides the mfn command based on the [`SDK`](https://knix.io/devtools/).

The latest version of the CLI is hosted at [`https://knix.io/devtools/`](https://knix.io/devtools/).
After downloading, one can install it:
``` sh
pip install --user mfn_sdk-0.8.0-py3-none-any.whl
pip install --user mfn_cli-0.8.0-py3-none-any.whl
```

## Using the cli

### mfn login

The login action is used to obtain a valid user token for all subsequent operations.
The token will be updated/stored in ~/.mfn/config.yaml

``` sh
mfn login [--url <url>] [--user <username>] [--password <password>]
```

``` sh
$ mfn login --url https://knix.io/mfn --user test@test
Logging into https://knix.io/mfn as user test@test
Please enter the password: ************
$ 
```
