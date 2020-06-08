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

# KNIX MicroFunctions automated integration tests

Each folder contains a bunch of Python unit tests that are run to verify a certain component/scenario/functionality.

Before running the tests, make sure that you have the correct settings.json or settings.env file.
They both contain the same information, so filling one is enough.
You can find the samples settings.json.sample and settings.env.sample in this folder.

For filling default values into a settings.json file, use:

`$ make settings`

To run the tests in a folder, use:

`$ make <foldername>`

e.g.,

`$ make helloworld`

The SDK tests can be configured to use a certain platform installation either through *environment variables* and/or a *settings.json file*.
Each test should obtain an MFNTest() instance from mfn_test_utils provided in the tests folder.
If you need additional functionality that requires MfnClient() from the SDK, then consider adding that functionality
in a general way to the mfn_test_utils.
The use of MfnClient() is discouraged to ensure a unified testing environment.

