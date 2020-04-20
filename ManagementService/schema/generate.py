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

from jsonschemacodegen import python as pygen
import json
import os

with open(os.path.dirname(os.path.realpath(__file__))+'/mfndata-workflow-schema.json') as fp:
    generator = pygen.GeneratorFromSchema('.')
    generator.Generate(json.load(fp), 'Workflow', 'workflow')