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
  angular.module('MfnWebConsole').controller('SetCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties) {

    var token = $cookies.get('token');
    var email = $cookies.get('email');
    var viewSetModalVisible = true;
    var urlPath = sharedProperties.getUrlPath();
    var storageLoc = sharedProperties.getStorageLocation();

    $scope.setItems = set();

     $scope.getSetName = function() {
         return sharedProperties.getSetName();
     }

     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceCodeEditor.focus();
       }, 350);

     }

     $scope.$on('$destroy', function(){
         viewSetModalVisible = false;
     });

     $scope.reloadSetItems = function() {
      var setname = sharedProperties.getSetName();
      console.log('Loading set:' + setname);

      var param_storage = {};
      param_storage["data_type"] = "set";
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = "retrieveset";
      param_storage["parameters"]["setname"] = setname;
      param_storage["workflowid"] = storageLoc.id;

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
          var objectData = response.data.data["setitems"] + "";

          $scope.setItems = set(objectData);
          console.log("set items: " + $scope.setItems);

          }
       }, function errorCallback(response) {
           console.log("Error occurred during retrieveset");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (viewSetModalVisible) {
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

       $scope.reloadSetValue();
       _editor.getSession().setValue("");

     };

     $scope.modifySetValue = function(modtype) {
      var setname = sharedProperties.getSetName();

       var objectDataStr = $scope.aceSession.getDocument().getValue().trim();
       if (objectDataStr == "")
       {
           return;
       }

       console.log('Updating set: ' + setname + " " + modtype + " " + objectDataStr);

      var param_storage = {};
      param_storage["data_type"] = "set";
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = modtype + "setentry";
      param_storage["parameters"]["setname"] = setname;
      param_storage["parameters"][modtype] = objectData;
      param_storage["workflowid"] = storageLoc.id;

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

             console.log('Set updated.');
             toastr.success('Set content updated!');
             //$scope.reloadStorageObjects();
           } else {
             console.log("Failure status returned by: " + modtype + "setentry");
             $scope.errorMessage = "An error occured while saving your object.";
             if (viewSetModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during " + modtype + "setentry");
           console.log(response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (viewSetModalVisible) {
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
