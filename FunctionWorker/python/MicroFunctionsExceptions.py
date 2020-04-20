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

'''
This file defines the Exception classes for MicroFunctions.
'''

class MicroFunctionsException(Exception):
    '''MicroFunctions root exception class'''

class MicroFunctionsWorkflowException(MicroFunctionsException):
    '''Raised when workflow definition has errors.'''

class MicroFunctionsFunctionCodeException(MicroFunctionsException):
    '''Raised when function code has errors.'''

class MicroFunctionsDataLayerException(MicroFunctionsException):
    '''Raised when access to data layer fails.'''

class MicroFunctionsUserLogException(MicroFunctionsException):
    '''Raised when logging has an exception.'''

class MicroFunctionsSessionAPIException(MicroFunctionsException):
    '''Raised when session function access has exceptions.'''
