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

    angular.module('MfnWebConsole.pages.profile')
    .controller('ProfileCtrl', ProfileCtrl);



    /** @ngInject */
    function ProfileCtrl($scope, $http, sharedProperties, sharedData, toastr, $cookies, $uibModal) {
        var urlPath = sharedProperties.getUrlPath();

        $scope.workflows = sharedData.getWorkflows();
        $scope.currentWorkflow = "";
        $scope.workflowUndeploymentModal = "";

        $scope.email = $cookies.get('email');
        $scope.name = $cookies.get('name');
        var token = $cookies.get('token');

        $scope.updateProfile = function() {

            var newName = $("#inputName").val();
            var password = $("#currentPassword").val();

            // name change
            if (newName && newName!=$scope.name) {
                if (!password) {
                    $scope.errorMessage = "Please enter your password."
                    $uibModal.open({
                        animation: true,
                        scope: $scope,
                        templateUrl: 'app/pages/workflows/modals/errorModal.html',
                        size: 'md',
                    });
                    return;
                } else {
                    changeName(password, newName);
                }
            } else {
                updatePassword();
            }
        };

        $scope.logOut = function() {
            document.cookie = "token=-1; path=/;";
            console.log('Logging out...');
            document.location.href="auth.html";
        }

        $scope.removeAccount = function() {

            var password = $("#currentPassword").val();

            if (!password) {
                $scope.errorMessage = "Please enter your password."
                $uibModal.open({
                    animation: true,
                    scope: $scope,
                    templateUrl: 'app/pages/workflows/modals/errorModal.html',
                    size: 'md',
                });
                return;
            } else {
                $uibModal.open({
                    animation: true,
                    scope: $scope,
                    templateUrl: 'app/pages/profile/modals/deleteAccountModal.html',
                    size: 'md',
                  });
            }
        };

        $scope.undeployAllWorkflows = function() {
            var password = $("#currentPassword").val();
            $("#currentPassword").val("");
            checkDeployedWorkflows(password);
        };

        $scope.clearPassword = function() {
            $("#currentPassword").val("");
        }

        function updatePassword() {
            var password = $("#currentPassword").val();
            var newPassword = $("#inputPassword").val();
            var newConfirmPassword = $("#inputConfirmPassword").val();
            // password change
            if (newPassword) {
                if (!password) {
                    $scope.errorMessage = "Please enter your current password."
                    $uibModal.open({
                        animation: true,
                        scope: $scope,
                        templateUrl: 'app/pages/workflows/modals/errorModal.html',
                        size: 'md',
                    });
                    return;
                }
                if (newPassword!=newConfirmPassword) {
                    $scope.errorMessage = "New passwords do not match."
                    $("#inputPassword").val("");
                    $("#inputConfirmPassword").val("");
                    $("#currentPassword").val("");
                    $uibModal.open({
                        animation: true,
                        scope: $scope,
                        templateUrl: 'app/pages/workflows/modals/errorModal.html',
                        size: 'md',
                    });
                    return;
                }
                if (newPassword!=password) {
                    $("#currentPassword").val("");
                    $("#inputPassword").val("");
                    $("#inputConfirmPassword").val("");
                    changePassword(password, newPassword);
                }
            }
            $("#currentPassword").val("");
        }

        function changeName(password, newName) {

            var req = {
              method: 'POST',
              url: urlPath,
              headers: {
                   'Content-Type': 'application/json'
              },
              data:   JSON.stringify({ "action" : "changeName", "data" : { "user" : { "email" : $scope.email, "password" : password, "new_name" : newName } } })
            }

            $http(req).then(function successCallback(response) {
                if (response.data.status=="success") {
                  console.log("Message:" + response.data.data.message);
                  $cookies.put('name', newName);
                  $scope.name = newName;
                  toastr.success('Your name has been updated successfully.');
                  updatePassword();
                } else {
                  console.log("Failure status returned by changeName request");
                  console.log("Message:" + response.data.data.message);
                  $("#currentPassword").val("");
                  $scope.errorMessage = response.data.data.message;
                  $uibModal.open({
                    animation: true,
                    scope: $scope,
                    templateUrl: 'app/pages/workflows/modals/errorModal.html',
                    size: 'md',
                  });
                }
            }, function errorCallback(response) {
                console.log("Error occurred during changeName request");
                console.log("Response:" + response);
                $("#currentPassword").val("");
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

        function deleteAccount(password) {

            if ($scope.workflowUndeploymentModal) {
                $scope.workflowUndeploymentModal.dismiss();
            }

            var req = {
              method: 'POST',
              url: urlPath,
              headers: {
                   'Content-Type': 'application/json'
              },

              data:   JSON.stringify({ "action" : "deleteAccount", "data" :  { "user" : { "password": password, "token" : token } } })

            }

            $http(req).then(function successCallback(response) {

                if (response.data.status=="success") {
                  console.log("Message:" + response.data.data.message);
                  $scope.logOut();

                } else {
                  console.log("Failure status returned by deleteAccount request");
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
                console.log("Error occurred during deleteAccount request");
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

        function checkDeployedWorkflows(password) {

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
                  var deployedWorkflows = false;
                  for (var i=0;i<$scope.workflows.length;++i) {
                    if ($scope.workflows[i].status=="deployed") {
                       undeployWorkflow(i, password);
                       deployedWorkflows = true;
                       break;
                    }
                  }
                  if (!deployedWorkflows) {
                    deleteAccount(password);
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
                  return true;
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
                return true;
            });
        }

        function undeployWorkflow(index, password) {
            var req;

            console.log('undeploying workflow ' + $scope.workflows[index].id);
            $scope.currentWorkflow = $scope.workflows[index].name;
            console.log($scope.currentWorkflow);
            if (!$scope.workflowUndeploymentModal) {
                $scope.workflowUndeploymentModal = $uibModal.open({
                    animation: true,
                    scope: $scope,
                    backdrop  : 'static',
                    keyboard  : false,
                    templateUrl: 'app/pages/profile/modals/workflowUndeploymentModal.html',
                    size: 'sm',
                });
            }
            $scope.workflows[index].status='undeploying';
            req = {
                method: 'POST',
                url: urlPath,
                headers: {
                'Content-Type': 'application/json'
                },
                data:   JSON.stringify({ "action" : "undeployWorkflow", "data" : { "user" : { "token" : token } , "workflow" : { "id" : $scope.workflows[index].id } } })
            }

            $http(req).then(function successCallback(response) {

                if (response.data.status=="success") {
                    setTimeout(function() {$scope.workflows[index].status='undeployed'; checkDeployedWorkflows(password); }, 2000);

                } else {
                    console.log("Failure status returned by undeployWorkflow");
                    console.log("Message:" + response.data.data.message);
                    $scope.workflowUndeploymentModal.dismiss();
                    $scope.errorMessage = response.data.data.message;
                    $uibModal.open({
                    animation: true,
                    scope: $scope,
                    templateUrl: 'app/pages/workflows/modals/errorModal.html',
                    size: 'md',
                    });
                }
            }, function errorCallback(response) {
                console.log("Error occurred during undeployWorkflow");
                console.log("Response:" + response);
                $scope.workflowUndeploymentModal.dismiss();
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

        function changePassword(password, newPassword) {

            var req = {
              method: 'POST',
              url: urlPath,
              headers: {
                   'Content-Type': 'application/json'
              },

              data:   JSON.stringify({ "action" : "changePassword", "data" : { "user" : { "email" : $scope.email, "password" : password, "new_password" : newPassword } } })

            }

            $http(req).then(function successCallback(response) {

                if (response.data.status=="success") {
                  console.log("Message:" + response.data.data.message);
                  toastr.success('Your password has been updated successfully.');
                } else {
                  console.log("Failure status returned by changePassword request");
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
                console.log("Error occurred during changePassword request");
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
    }

})();