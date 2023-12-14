/*
   Copyright 2021 The KNIX Authors

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

(function () {
  'use strict';

  angular.module('MfnWebConsole.pages.functions')
      .controller('FunctionTableCtrl', FunctionTableCtrl);

  /** @ngInject */
  function FunctionTableCtrl($scope, $http, $cookies, $filter, editableOptions, editableThemes, $interval, $uibModal, baProgressModal, toastr, sharedProperties, sharedData) {

    var urlPath = sharedProperties.getUrlPath();
    //console.log('Path:' + urlPath);

    var dataPrefix = sharedProperties.getDataPrefix();
    var promise = undefined;

    $scope.itemsByPage=10;

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    $scope.open = function (page, size, cFunction, cFunctionName, cFunctionStatus, cFunctionRuntime, message) {
      sharedProperties.setFunctionId(cFunction);
      sharedProperties.setFunctionName(cFunctionName);
      sharedProperties.setFunctionStatus(cFunctionStatus);
      sharedProperties.setFunctionRuntime(cFunctionRuntime);
      $scope.errorMessage = message;
      $uibModal.open({
        animation: true,
        scope: $scope,
        backdrop  : 'static',
        keyboard  : false,
        templateUrl: page,
        size: size,
      });

    };

    var token = $cookies.get('token');

    $scope.functions = sharedData.getFunctions();

    if (!$scope.functions) {
      getFunctions();
    }

    $scope.runtimes = [
      {value: 'Python 3.6', text: 'Python 3.6'},
      {value: 'Java', text: 'Java'}

    ];

    $scope.versions = [
      { }
    ];

    $scope.navigate = function(event,rowform,mFunction) {

      if (event.keyCode==13) {
        rowform.$submit();
      }

    }


    function getFunctions() {

      var req = {
        method: 'POST',
        url: urlPath,
        headers: {

              'Content-Type': 'application/json'

        },

        data:   JSON.stringify({ "action" : "getFunctions", "data" : { "user" : { "token" : token } } })

      }

      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {
            $scope.functions = response.data.data.functions;

            sharedData.setFunctions(response.data.data.functions);
          } else {
            console.log("Failure status returned by getFunctions");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during getFunctions");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });

      });
    }

    $scope.getIndex = function(mFunction) {
      return $scope.functions.indexOf(mFunction);
    }

    $scope.showVersion = function(mFunction) {
      if(mFunction.version && $scope.versions.length) {
        var selected = $filter('filter')($scope.versions, {id: mFunction.version});
        return selected.length ? mFunction.version : 'Not set';
      } else return 'Not set'
    };

    function dateFormat(d) {
      var format = "d-m-Y H:i:s";
      return format

        .replace(/d/gm, ('0' + (d.getDate())).substr(-2))
        .replace(/m/gm, monthNames[d.getMonth()])
        .replace(/Y/gm, d.getFullYear().toString())
        .replace(/H/gm, ('0' + (d.getHours() + 0)).substr(-2))
        .replace(/i/gm, ('0' + (d.getMinutes() + 0)).substr(-2))
        .replace(/s/gm, ('0' + (d.getSeconds() + 0)).substr(-2));
    }

    $scope.showLastModified = function(mFunction) {
      if(mFunction.modified && mFunction.modified!=0) {
          //return dateFormat(new Date(parseFloat(mFunction.modified)));
          var timeStamp = mFunction.modified.toString();
          if (timeStamp.indexOf('.')>0) {
            timeStamp = timeStamp.substr(0, timeStamp.indexOf('.'));
          }
          return dateFormat(new Date(parseFloat(timeStamp)*1000));
      } else return 'Not set';
    };

    $scope.showRuntime= function(mFunction) {
      var selected = [];
      if(mFunction.runtime) {
        selected = $filter('filter')($scope.runtimes, {value: mFunction.runtime});
      }
      return selected.length ? mFunction.runtime : 'Not set';
    };

    function createTemporaryWorkflow(functionIndex) {
      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
          'Content-Type': 'application/json'
        },
        data:   JSON.stringify({ "action" : "addWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "name" : 'mfn-internal-' + $scope.functions[functionIndex].id } } })
      }
      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {
            console.log('new workflow id:' + response.data.data.workflow.id);
            saveTemporaryWorkflowJSON(functionIndex, response.data.data.workflow.id);
          } else {
            console.log("Failure status returned by addWorkflow");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during addWorkflow");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });
      });
    }

    function saveTemporaryWorkflowJSON(functionIndex, workflowId) {

      var encodedWorkflowJSON = btoa('{\r\t"name": "' + 'mfn-internal-' + workflowId + '",\r\t"entry": "' + $scope.functions[functionIndex].name + '",\r\t"exit": "wfExit",\r\t"functions": [\r\t\t{\r\t\t\t"name": "' + $scope.functions[functionIndex].name + '",\r\t\t\t"next": ["wfExit"]\r\t\t}\r\t]\r}');
      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
           'Content-Type': 'application/json'
        },
        data:   JSON.stringify({ "action" : "uploadWorkflowJSON", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId, "json" : encodedWorkflowJSON } } })
      }
      $http(req).then(function successCallback(response) {

      if (response.data.status=="success") {
            console.log('Workflow JSON sucessfully uploaded.');
            deployTemporaryWorkflow('deploy', functionIndex, workflowId);
          } else {
            console.log("Failure status returned by uploadWorkflowJSON");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during uploadWorkflowJSON");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });

      });

    }

    function deployTemporaryWorkflow(action, functionIndex, workflowId) {
      var req;
      //console.log('deployWorkflow,' + action + ',' + index + ',' + $scope.workflows[index].status);
      if (action=='deploy') {

        console.log('deploying workflow ' + workflowId);


        req = {
          method: 'POST',
          url: urlPath,
          headers: {
            'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "deployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId } } })
        }
      } else {
        console.log('undeploying workflow ' + workflowId);

        req = {
          method: 'POST',
          url: urlPath,
          headers: {
            'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "undeployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId } } })
        }
      }
      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {
            if (action=="deploy") {
              //$scope.workflows[index].status='deploying';
              promise = $interval(function(){checkWorkflowDeploymentStatus(functionIndex, workflowId);}, 2000);
              //toastr.success('Your workflow has been deployed successfully!');
              //$scope.reloadWorkflows();
              //setTimeout(function() { loadWorkflows(functionIndex, workflowId);}, 2000);
            } else {
              setTimeout(function() { deleteTemporaryWorkflow(functionIndex, workflowId);}, 2000);
              //$scope.reloadWorkflows();

            }
          } else {
            console.log("Failure status returned by deploy/undeployWorkflow");
            console.log("Message:" + response.data.data.message);
            /*if (action=="deploy") {
              $scope.workflows[index].status='undeployed';
            }*/
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during deploy/undeployWorkflow");
          console.log("Response:" + response);
          if (action=="deploy") {
            $scope.workflows[index].status='undeployed';
          }
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }

          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });

      });

    }

    function deleteTemporaryWorkflow(functionIndex, workflowId) {

    }

    function checkWorkflowDeploymentStatus(functionIndex, workflowId) {
      var req;
      //console.log('checkWorkflowDeploymentStatus,' + index + ',' + $scope.workflows[index].status);


        console.log('checking workflow status for workflow ' + workflowId);

        req = {
          method: 'POST',
          url: urlPath,
          headers: {
           'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "getWorkflows", "data" : { "user" : { "token" : token } , "workflow" : { "id" : workflowId } } })
        }

      $http(req).then(function successCallback(response) {
          if (response.data.status=="success") {

            if (response.data.data.workflow.status=='deployed') {
              $interval.cancel(promise);
              testWorkflow(functionIndex, workflowId, response.data.data.workflow.endpoints[0]);
            }
            else if (response.data.data.workflow.status=='failed')
            {
                $interval.cancel(promise);
                $scope.functionDeploymentModal.dismiss();
                setTimeout(function() { deleteTemporaryWorkflow(functionIndex, workflowId);}, 2000);
                console.log("Error in deployment: " + response.data.data.workflow.deployment_error);
                $scope.errorMessage = response.data.data.workflow.deployment_error;
                $uibModal.open({
                  animation: true,
                  scope: $scope,
                  templateUrl: 'app/pages/workflows/modals/errorModal.html',
                  size: 'md',
                });
            }
          } else {
            console.log("Failure status returned by getWorkflowStatus");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during getWorkflowStatus");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });
      });


    }


    function loadWorkflows(functionIndex, workflowId) {
      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
              'Content-Type': 'application/json'
        },
        data:   JSON.stringify({ "action" : "getWorkflows", "data" : { "user" : { "token" : token } } })
      }

      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {

            var wflows = response.data.data.workflows;
            for (var i=0;i<wflows.length;i++) {
              if (wflows[i].id == workflowId) {
                testWorkflow(functionIndex, workflowId, wflows[i].endpoints[0]);
                break;
              }
            }

          } else {
            console.log("Failure status returned by getWorkflows");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during getWorkflows");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });

      });
    }

    function testWorkflow(functionIndex, workflowId, workflowUrl) {
      sharedProperties.setWorkflowId(workflowId);
      sharedProperties.setWorkflowName($scope.functions[functionIndex].name + "   ");
      sharedProperties.setWorkflowStatus('deployed');
      sharedProperties.setWorkflowUrl(workflowUrl);

      $scope.functionDeploymentModal.dismiss();
      $uibModal.open({
        animation: true,
        scope: $scope,
        backdrop  : 'static',
        keyboard  : false,
        templateUrl: 'app/pages/functions/modals/functionTestModal.html',
        size: 'lg',
      });

    }

    $scope.testFunction = function(index) {
      sharedProperties.setFunctionId($scope.functions[index].id);
      sharedProperties.setFunctionName($scope.functions[index].name);
      sharedProperties.setFunctionRuntime($scope.functions[index].runtime);
      $scope.functionDeploymentModal = $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/functions/modals/functionDeploymentModal.html',
        size: 'sm',
      });
      createTemporaryWorkflow(index);
    }

    $scope.deleteFunction = function(index) {
      console.log('deleting function ' + $scope.functions[index].id);

      var req = {
        method: 'POST',
        url: urlPath,
        headers: {

            'Content-Type': 'application/json'

        },

        data:   JSON.stringify({ "action" : "deleteFunction", "data" : { "user" : { "token" : token } , "function" : { "id" : $scope.functions[index].id } } })

      }
      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {
            console.log('Function sucessfully deleted.');
            toastr.success('Your function has been deleted successfully!');
            $scope.functions.splice(index, 1);
          } else {
            console.log("Failure status returned by deleteFunction");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during deleteFunction");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });

      });

    }


    $scope.removeFunction = function(index) {
      $scope.functionToBeDeleted = $scope.functions[index];
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/functions/modals/deleteFunctionModal.html',
        size: 'md',
      });


    };

    $scope.gotoPage = function(page) {

      angular
       .element( $('#functionPagination') )
       .isolateScope()
       .selectPage(page);

    }

    $scope.reloadFunctions = function() {
      var req = {
        method: 'POST',
        url: urlPath,
        headers: {

              'Content-Type': 'application/json'

        },

        data:   JSON.stringify({ "action" : "getFunctions", "data" : { "user" : { "token" : token } } })

      }

      $http(req).then(function successCallback(response) {
          //console.log(response.data);
          //console.log(response.data.data.functions);

          if (response.data.status=="success") {
            $scope.functions = response.data.data.functions;
            sharedData.setFunctions(response.data.data.functions);
          } else {
            console.log("Failure status returned by getFunctions");
            console.log("Message:" + response.data.data.message);
            $scope.errorMessage = response.data.data.message;
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during getFunctions");
          console.log("Response:" + response);
          if (response.statusText) {
            $scope.errorMessage = response.statusText;
          } else {
            $scope.errorMessage = response;
          }
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });

      });

    }

    // save function modifications
    $scope.saveFunction = function(mFunction) {

      var token = $cookies.get('token');


      if (mFunction.id=='-1')
      {
        console.log('creating new function ' + mFunction.name);

        var req = {
          method: 'POST',
          url: urlPath,
          headers: {

            'Content-Type': 'application/json'

          },

		data:   JSON.stringify({ "action" : "addFunction", "data" : { "user" : { "token" : token } , "function" : { "name" : mFunction.name, "runtime" : mFunction.runtime, "gpu_usage": mFunction.gpu_usage, "gpu_mem_usage": mFunction.gpu_mem_usage } } })

        }
        $http(req).then(function successCallback(response) {

            if (response.data.status=="success") {
              mFunction.id = response.data.data.function.id;
              console.log('new function id:' + response.data.data.function.id);
              toastr.success('Your function has been created successfully!');
              $scope.reloadFunctions();
              $scope.open('app/pages/functions/modals/codeEditorModal.html', 'lg', mFunction.id, mFunction.name, mFunction.status, mFunction.runtime, mFunction.gpu_usage, mFunction.gpu_mem_usage);

            } else {
              console.log("Failure status returned by addFunction");
              console.log("Message:" + response.data.data.message);
              $scope.reloadFunctions();
              $scope.errorMessage = response.data.data.message;
              $uibModal.open({
                animation: true,
                scope: $scope,
                templateUrl: 'app/pages/workflows/modals/errorModal.html',
                size: 'md',
              });
            }
        }, function errorCallback(response) {
            console.log("Error occurred during addFunction");
            console.log("Response:" + response);
            $scope.reloadFunctions();
            if (response.statusText) {
              $scope.errorMessage = response.statusText;
            } else {
              $scope.errorMessage = response;
            }
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });

        });

      } else {
        console.log('modifying function: ' + mFunction.name);



        var req = {
          method: 'POST',
          url: urlPath,
          headers: {

            'Content-Type': 'application/json'

          },

		data:   JSON.stringify({ "action" : "modifyFunction", "data" : { "user" : { "token" : token } , "function" : { "id": mFunction.id, "name" : mFunction.name, "runtime" : mFunction.runtime, "gpu_usage" : mFunction.gpu_usage, "gpu_mem_usage": mFunction.gpu_mem_usage } } })

        }
        $http(req).then(function successCallback(response) {

            if (response.data.status=="success") {
              toastr.success('Your function has been saved successfully!');
              $scope.reloadFunctions();
            } else {
              console.log("Failure status returned by modifyFunction");
              console.log("Message:" + response.data.data.message);
              $scope.errorMessage = response.data.data.message;
              $uibModal.open({
                animation: true,
                scope: $scope,
                templateUrl: 'app/pages/workflows/modals/errorModal.html',
                size: 'md',
              });
            }
        }, function errorCallback(response) {
            console.log("Error occurred during modifyFunction");
            console.log("Response:" + response);
            if (response.statusText) {
              $scope.errorMessage = response.statusText;
            } else {
              $scope.errorMessage = response;
            }
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });

        });
      }
    };



    $scope.addFunction = function() {
      $scope.inserted = {
        id: '-1',
        name: '',
        status: 'undeployed',
        runtime: 'Python 3.6',
        gpu_usage: '0',
        gpu_mem_usage: '0',
        modified: '0'
      };
      $scope.functions.push($scope.inserted);
      $scope.gotoPage(1);
    };

    editableOptions.theme = 'bs3';
    editableThemes['bs3'].submitTpl = '<button type="submit" class="btn btn-primary btn-with-icon"><i class="ion-checkmark-round"></i></button>';
    editableThemes['bs3'].cancelTpl = '<button type="button" ng-click="$form.$cancel()" class="btn btn-default btn-with-icon"><i class="ion-close-round"></i></button>';


  }

})();
