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

(function () {
  'use strict';

  angular.module('MfnWebConsole.pages.workflows')
      .controller('WorkflowTableCtrl', WorkflowTableCtrl);

  function WorkflowTableCtrl($scope, $http, $cookies, $filter, editableOptions, editableThemes, $uibModal, $timeout, $interval, baProgressModal, toastr, sharedProperties, sharedData) {

    var urlPath = sharedProperties.getUrlPath();
    var promise = undefined;

    var dataPrefix = sharedProperties.getDataPrefix();


    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    $scope.open = function (page, size, cWorkflow, cWorkflowName, cWorkflowStatus, cWorkflowUrl, codeError, message) {
      sharedProperties.setWorkflowId(cWorkflow);
      sharedProperties.setWorkflowName(cWorkflowName);
      sharedProperties.setWorkflowStatus(cWorkflowStatus);
      sharedProperties.setWorkflowUrl(cWorkflowUrl);
      sharedProperties.setCodeError(codeError);
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

    $scope.workflowToBeImported = "";
    $scope.itemsByPage=10;
    var token = $cookies.get('token');

    $scope.workflows = sharedData.getWorkflows();

    if (!$scope.workflows) {
      getWorkflows();
    }



    $scope.workflowToBeImported = getParameterByName('importWorkflow');
    if ($scope.workflowToBeImported) {
      $scope.open('app/pages/workflows/modals/importWorkflowModal.html', 'lg');
    }

    $scope.navigate = function(event,rowform,workflow) {
      if (event.keyCode==13) {
        rowform.$submit();
      }
    }

    function getParameterByName(name) {
      var match = RegExp('[?&]' + name + '=([^&]*)').exec(window.location.search);
      return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
    }

    function getWorkflows() {

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
            $scope.workflows = response.data.data.workflows;
            sharedData.setWorkflows(response.data.data.workflows);
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

    $scope.showLastModified = function(workflow) {
      if(workflow.modified && workflow.modified!=0) {
          var timeStamp = workflow.modified.toString();
          if (timeStamp.indexOf('.')>0) {
            timeStamp = timeStamp.substr(0, timeStamp.indexOf('.'));
          }
          return dateFormat(new Date(parseFloat(timeStamp)*1000));
      } else return 'Not set';
    };

    $scope.showCompatibility = function(workflow) {
      if(workflow.ASL_type) {
          return workflow.ASL_type;
      } else return 'unknown';
    };

    $scope.progressFunction = function() {
       return $timeout(function() {}, 1000);
    };

    $scope.gotoPage = function(page) {

      angular
       .element( $('#workflowPagination') )
       .isolateScope()
       .selectPage(page);

    }

    $scope.getIndex = function(workflow) {
      return $scope.workflows.indexOf(workflow);
    }

    $scope.showEndpoint = function(workflow) {
      if (workflow.endpoints && workflow.status=='deployed') {
        return workflow.endpoints[0];
      } else return 'Not set';
    };

    $scope.showStatus= function(workflow) {
      if (workflow.status) {
        return workflow.status;
      }
      return 'Not set';
    };

    $scope.workflowDeployed = function(index) {
      if ($scope.workflows[index].status=='deployed') {
        return true;
      } else {
        return false;
      }
    };

    $scope.workflowBeingDeployed = function(index) {
      if ($scope.workflows[index].status=='deploying') {
        return true;
      } else {
        return false;
      }
    };

    $scope.workflowBeingUndeployed = function(index) {
      if ($scope.workflows[index].status=='undeploying') {
        return true;
      } else {
        return false;
      }
    };

    $scope.showButtonLabel= function(workflow) {

      if (workflow.status=='deployed') {
        return 'Undeploy';
      } else {
        return 'Deploy';
      }

    };

    $scope.removeWorkflow = function(index) {
      $scope.workflowToBeDeleted = $scope.workflows[index];
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/workflows/modals/deleteWorkflowModal.html',
        size: 'md',
      });


    };



    $scope.deleteWorkflow = function(index) {
      console.log('deleting workflow ' + $scope.workflows[index].id);


      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
           'Content-Type': 'application/json'
        },
        data:   JSON.stringify({ "action" : "deleteWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : $scope.workflows[index].id } } })
      }
      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {
            console.log('Workflow sucessfully deleted.');
            toastr.success('Your workflow has been deleted successfully!');
            $scope.workflows.splice(index, 1);
          } else {
            console.log("Failure status returned by deleteWorkflow");
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
          console.log("Error occurred during deleteWorkflow");
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

    };

    $scope.checkWorkflowDeploymentStatus = function(index, action) {
      var req;
      //console.log('checkWorkflowDeploymentStatus,' + index + ',' + $scope.workflows[index].status);
      if ($scope.workflows[index].status=='deploying') {

        console.log('checking workflow status for workflow ' + $scope.workflows[index].id);

        req = {
          method: 'POST',
          url: urlPath,
          headers: {
           'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "getWorkflows", "data" : { "user" : { "token" : token } , "workflow" : { "id" : $scope.workflows[index].id } } })
        }

      $http(req).then(function successCallback(response) {
          if (response.data.status=="success") {

            if (response.data.data.workflow.status=='deployed') {
              $interval.cancel(promise);
              if ($scope.workflows[index].status=='deployed') {
                return;
              }
              $scope.workflows[index].status='deployed';
              $scope.workflows[index].endpoints[0]=response.data.data.workflow.endpoints[0];
              toastr.success('Your workflow has been deployed successfully!');
              //$scope.reloadWorkflows();
              if (action=="deployAndExecute") {
                //setTimeout(function() {$scope.workflowDeploymentModal.dismiss();$scope.open('app/pages/workflows/modals/workflowExecutionModal.html', 'lg', $scope.workflows[index].id, $scope.workflows[index].name, $scope.workflows[index].status, $scope.workflows[index].endpoint);}, 1100);
                $scope.workflowDeploymentModal.dismiss();$scope.open('app/pages/workflows/modals/workflowExecutionModal.html', 'lg', $scope.workflows[index].id, $scope.workflows[index].name, $scope.workflows[index].status, $scope.workflows[index].endpoints[0]);
              }
            }
            else if (response.data.data.workflow.status=='failed')
            {
                $interval.cancel(promise);
                $scope.workflows[index].status="failed";
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

      } else {
        $interval.cancel(promise);
      }
    };

    $scope.deployWorkflow = function(index, action, version) {
      var req;
      //console.log('deployWorkflow,' + action + ',' + index + ',' + $scope.workflows[index].status);
      if (action=='deploy' || action=='deployAndExecute') {

        console.log('deploying workflow ' + $scope.workflows[index].id);
        $scope.workflows[index].status='deploying';

        var dat = { "action" : "deployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : $scope.workflows[index].id} } };

        if (version) {
          dat.data.workflow.version = version;
          
        }

        req = {
          method: 'POST',
          url: urlPath,
          headers: {
           'Content-Type': 'application/json'
          },
          //data:   JSON.stringify({ "action" : "deployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : $scope.workflows[index].id } } })
          data:   JSON.stringify(dat)
        }
      } else {
        console.log('undeploying workflow ' + $scope.workflows[index].id);
        $scope.workflows[index].status='undeploying';
        req = {
          method: 'POST',
          url: urlPath,
          headers: {
           'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "undeployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : $scope.workflows[index].id } } })
        }
      }
      $http(req).then(function successCallback(response) {

          if (response.data.status=="success") {
            if (action=="deploy"||action=="deployAndExecute") {
              //$scope.workflows[index].status='deploying';
              promise = $interval(function(){$scope.checkWorkflowDeploymentStatus(index, action);}, 2000);
              //toastr.success('Your workflow has been deployed successfully!');
              //$scope.reloadWorkflows();
            } else {
              setTimeout(function() {$scope.workflows[index].status='undeployed'; toastr.success('Your workflow has been undeployed successfully!');}, 2000);
              if (action=='redeployAndExecute') {
                  setTimeout(function() {$scope.deployWorkflow(index, 'deployAndExecute', version);}, 2100);
              }

              //$scope.reloadWorkflows();

            }
          } else {

            console.log("Failure status returned by deploy/undeployWorkflow");
            console.log("Message:" + response.data.data.message);
            if (action=="deploy" || action=="deployAndExecute") {
              $scope.workflows[index].status='undeployed';
            }
            if (action=="redeployAndExecute" || action=="deployAndExecute") {
              $scope.workflowDeploymentModal.dismiss();
            }
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
          if (action=="deploy" || 'deployAndExecute') {
            $scope.workflows[index].status='undeployed';
          }
          if (action=="redeployAndExecute" || action=="deployAndExecute") {
            $scope.workflowDeploymentModal.dismiss();
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

    };

    $scope.reloadWorkflows = function() {
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
            $scope.workflows = response.data.data.workflows;
            sharedData.setWorkflows(response.data.data.workflows);
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

    // save workflow modifications
    $scope.saveWorkflow = function(workflow) {

      var token = $cookies.get('token');


      if (workflow.id=='-1')
      {
        console.log('creating new workflow ' + workflow.name);

        var req = {
          method: 'POST',
          url: urlPath,
          headers: {
           'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "addWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "name" : workflow.name } } })
        }
        $http(req).then(function successCallback(response) {

            if (response.data.status=="success") {
              workflow.id = response.data.data.workflow.id;
              console.log('new workflow id:' + response.data.data.workflow.id);
              console.log('new workflow version:' + response.data.data.workflow.version_latest);
              toastr.success('Your workflow has been created successfully!');
              $scope.reloadWorkflows();
              $scope.open('app/pages/workflows/modals/workflowEditorModal.html', 'lg', workflow.id, workflow.name, workflow.status);
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

      } else {
        console.log('modifying workflow: ' + workflow.name);

        var req = {
          method: 'POST',
          url: urlPath,
          headers: {
           'Content-Type': 'application/json'
          },
          data:   JSON.stringify({ "action" : "modifyWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id": workflow.id, "name" : workflow.name } } })
        }
        $http(req).then(function successCallback(response) {

            if (response.data.status=="success") {
              toastr.success('Your workflow has been saved successfully!');
              $scope.reloadWorkflows();
            } else {
              console.log("Failure status returned by modifyWorkflow");
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
            console.log("Error occurred during modifyWorkflow");
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

    $scope.importWorkflow = function() {

        $scope.open('app/pages/workflows/modals/importWorkflowModal.html', 'lg');

    };

    $scope.openWorkflowExecutionModal = function(workflowId) {
      for (var key in $scope.workflows) {
        if ($scope.workflows[key].id==workflowId) {
          var index = key;
          if ($scope.workflows[index].status=='deployed') {
            $scope.open('app/pages/workflows/modals/workflowExecutionModal.html', 'lg', $scope.workflows[index].id, $scope.workflows[index].name, $scope.workflows[index].status, $scope.workflows[index].endpoint);
          }
        }
      }
    }

    $scope.deployAndExecuteWorkflow = function(workflowId, version) {

      for (var key in $scope.workflows) {
        if ($scope.workflows[key].id==workflowId) {
          var index = key;
          if ($scope.workflows[index].status=='deployed') {
            $scope.actionLabel = "Redeploying";
            $scope.workflowDeploymentModal = $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/workflowDeploymentModal.html',
              size: 'sm',
            });
            $scope.deployWorkflow(index, 'redeployAndExecute', version);
          } else {
            $scope.actionLabel = "Deploying";
            $scope.workflowDeploymentModal = $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/workflowDeploymentModal.html',
              size: 'sm',
            });
            $scope.deployWorkflow(index, 'deployAndExecute', version);
          }
          break;
        }
      }

    }

    $scope.addWorkflow = function() {
      $scope.inserted = {
        id: '-1',
        name: '',
        status: 'undeployed',
        endpoint: null
      };
      $scope.workflows.push($scope.inserted);
      $scope.gotoPage(1);
    };

    editableOptions.theme = 'bs3';
    editableThemes['bs3'].submitTpl = '<button type="submit" class="btn btn-primary btn-with-icon"><i class="ion-checkmark-round"></i></button>';
    editableThemes['bs3'].cancelTpl = '<button type="button" ng-click="$form.$cancel()" class="btn btn-default btn-with-icon"><i class="ion-close-round"></i></button>';


  }

})();
