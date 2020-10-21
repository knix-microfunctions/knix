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

(function() {
  angular.module('MfnWebConsole').controller('CounterCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties) {

    var token = $cookies.get('token');
    var email = $cookies.get('email');
    var viewCounterModalVisible = true;
    var urlPath = sharedProperties.getUrlPath();
    var storageLoc = sharedProperties.getStorageLocation();

    $scope.counterValue = "0";

     $scope.getCounterName = function() {
         return sharedProperties.getCounterName();
     }

     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceCodeEditor.focus();
       }, 350);

     }

     $scope.$on('$destroy', function(){
         viewCounterModalVisible = false;
     });

     $scope.reloadCounterValue = function() {
      var countername = sharedProperties.getCounterName();
      console.log('Loading counter:' + countername);

      var param_storage = {};
      param_storage["data_type"] = "counter";
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = "getcounter";
      param_storage["parameters"]["countername"] = countername;
      param_storage["workflowid"] = storageLoc;

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : param_storage } })
       }

       $http(req).then(function successCallback(response) {

          if (response.data.status == "success")
          {

          console.log('Storage object successfully downloaded.');
          var objectData = response.data.data["countervalue"] + "";

          $scope.counterValue = objectData + "";
          console.log("counter value: " + $scope.counterValue);

          }
       }, function errorCallback(response) {
           console.log("Error occurred during getData");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (viewCounterModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });

     }

     $scope.aceLoaded = function(_editor) {
        $scope.aceSession = _editor.getSession();
       $scope.aceCodeEditor = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.focus();

       $scope.reloadCounterValue();
       _editor.getSession().setValue("");

     };

     $scope.modifyCounterValue = function(modtype) {
      var countername = sharedProperties.getCounterName();

       var objectDataStr = $scope.aceSession.getDocument().getValue().trim();
       console.log(objectDataStr);
       if (objectDataStr == "")
       {
           return;
       }

       var objectData = 0;
       objectData = parseInt(objectDataStr);
       if (isNaN(objectData) || !isFinite(objectData))
       {
           return;
       }
       console.log('Updating counter: ' + countername + " " + modtype + " " + objectData);

      var param_storage = {};
      param_storage["data_type"] = "counter";
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = modtype + "counter";
      param_storage["parameters"]["countername"] = countername;
      param_storage["parameters"][modtype] = objectData;
      param_storage["workflowid"] = storageLoc;

      var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : param_storage } })
       }

       $http(req).then(function successCallback(response) {

         if (response.data.status=="success") {

             console.log('Counter updated.');
             toastr.success('Counter value updated!');
             //$scope.reloadStorageObjects();
           } else {
             console.log("Failure status returned by: " + modtype + " counter");
             $scope.errorMessage = "An error occured while saving your object.";
             if (viewCounterModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during putData");
           console.log(response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (viewCounterModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     };

    });
}());
