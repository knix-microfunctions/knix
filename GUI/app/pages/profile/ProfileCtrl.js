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