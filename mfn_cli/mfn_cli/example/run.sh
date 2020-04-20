#!/bin/bash
#   Copyright 2020 The KNIX Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

mfn login
mfn create function my_function myfunction.py
mfn create workflow my_workflow myworkflow.json
mfn deploy workflow my_workflow
mfn execute workflow my_workflow "HUI"
mfn logs my_workflow
mfn undeploy my_workflow
mfn delete workflow my_workflow
mfn delete function my_function