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


'use strict';

var app = angular.module('MfnWebConsole', [
  'ngAnimate',
  'ui.ace',
  'ngCookies',
  'ngclipboard',
  'ui.bootstrap',
  'ui.sortable',
  'ui.router',
  'ngTouch',
  'toastr',
  'smart-table',
  "xeditable",
  'ui.slimscroll',
  'angular-progress-button-styles',
  'BlurAdmin.theme',
  'MfnWebConsole.pages'
]).service('sharedProperties', function () {
    var functionId = '';
    var functionStatus = '';
    var functionName = '';
    var functionRuntime = '';
    var workflowId = '';
    var workflowStatus = '';
    var workflowName = '';
    var workflowUrl = '';
    var objectKey = '';
    var codeError = '';

    var urlPath = "/management";
    var dataPrefix = "value=";

    return {

        getDataPrefix: function() {
          return dataPrefix;
        },

        getUrlPath: function () {
          return urlPath;
        },
        getFunctionId: function () {
            return functionId;
        },
        getFunctionRuntime: function () {
            return functionRuntime;
        },
        setFunctionId: function(id) {
            functionId = id;
        },
        getFunctionName: function () {
            return functionName;
        },
        getFunctionStatus: function () {
            return functionStatus;
        },
        setFunctionName: function(name) {
            functionName = name;
        },
        setFunctionStatus: function(status) {
            functionStatus = status;
        },
        setFunctionRuntime: function(runtime) {
            functionRuntime = runtime;
        },
        getWorkflowId: function () {
            return workflowId;
        },
        getWorkflowName: function () {
            return workflowName;
        },
        getWorkflowStatus: function () {
            return workflowStatus;
        },
        getWorkflowUrl: function(url) {
            return workflowUrl;
        },
        setWorkflowId: function(id) {
            workflowId = id;
        },
        setWorkflowName: function(name) {
            workflowName = name;
        },
        setWorkflowUrl: function(url) {
            workflowUrl = url;
        },
        setWorkflowStatus: function(status) {
            workflowStatus = status;
        },
        getObjectKey: function() {
          return objectKey;
        },
        setObjectKey: function(key) {
          objectKey = key;
        },
        getCodeError: function() {
          return codeError;
        },
        setCodeError: function(error) {
          codeError = error;
        }

    };
});

app.factory('sharedData', function(){
  var functions = [ ];
  var workflows = [ ];
  var storageObjects = [ ];
  var workflowExecutionInputEditor = new Map();
  var workflowExecutionInput = new Map();
  return {
    getFunctions: function () {
        return this.functions;
    },
    setFunctions: function(functions) {
      this.functions = functions;
    },
    getWorkflows: function () {
        return this.workflows;
    },
    setWorkflows: function(workflows) {
      this.workflows = workflows;
    },
    getStorageObjects: function () {
        return this.storageObjects;
    },
    setStorageObjects: function(storageObjects) {
      this.storageObjects = storageObjects;
    },
    getWorkflowExecutionInput: function (id) {
        if (workflowExecutionInput && workflowExecutionInput.has(id)) {
          return workflowExecutionInput.get(id);
        } else {
          return "";
        }
    },
    setWorkflowExecutionInput: function(id, workflowInput) {
      workflowExecutionInput.set(id, workflowInput);
    },
    getWorkflowExecutionInputEditor: function (id) {
      if (workflowExecutionInputEditor && workflowExecutionInputEditor.has(id)) {
        return workflowExecutionInputEditor.get(id);
      } else {
        return "";
      }
    },
    setWorkflowExecutionInputEditor: function(id, workflowInputEditor) {
      workflowExecutionInputEditor.set(id, workflowInputEditor);
    }
  };
});

app.run(function ($rootScope, $window, $cookies) {

  $rootScope.$on('$stateChangeStart', function (event, toState, toParams) {

    var token = $cookies.get('token');
    //console.log(token);
    if (!token || token=="-1") {
      event.preventDefault();
      $window.location.href="auth.html";

    }
   
  });

});
