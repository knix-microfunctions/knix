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
  angular.module('MfnWebConsole').controller('MapCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties) {

    var token = $cookies.get('token');
    var email = $cookies.get('email');
    var viewMapModalVisible = true;
    var urlPath = sharedProperties.getUrlPath();
    var storageLoc = sharedProperties.getStorageLocation();

    $scope.mapEntries = {};

     $scope.getMapName = function() {
         return sharedProperties.getMapName();
     }

     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceCodeEditor.focus();
       }, 350);

     }

     $scope.$on('$destroy', function(){
         viewMapModalVisible = false;
     });

     $scope.reloadMapEntries = function() {
      var mapname = sharedProperties.getMapName();
      console.log('Loading map:' + mapname);

      var param_storage = {};
      param_storage["data_type"] = "map";
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = "retrievemap";
      param_storage["parameters"]["mapname"] = mapname;
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
          $scope.mapEntries = response.data.data["mapentries"];

          console.log("map entries: %o", $scope.mapEntries);

          }
       }, function errorCallback(response) {
           console.log("Error occurred during retrievemap");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (viewMapModalVisible) {
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
         $scope._editor = _editor;
        $scope.aceSession = _editor.getSession();
       $scope.aceCodeEditor = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.focus();

       $scope.reloadMapEntries();
       _editor.getSession().setValue("");

     };

      $scope.containsMapKey = function() {
       var objectDataStr = document.getElementById("map_key").value;
       if (objectDataStr == "")
       {
           return undefined;
       }
       if (objectDataStr in $scope.mapEntries)
       {
           return true;
       }
       else
       {
           return false;
       }
     }

    $scope.modifyMapEntries = function(modtype) {
      var mapname = sharedProperties.getMapName();

      var param_storage = {};
      param_storage["data_type"] = "map";
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = modtype + "mapentry";
      param_storage["parameters"]["mapname"] = mapname;
      var map_key = document.getElementById("map_key").value;
      param_storage["parameters"]["key"] = map_key;
      if (modtype == "put")
      {
          var map_value = document.getElementById("map_value").value;
          param_storage["parameters"]["value"] = map_value;
      }
      param_storage["workflowid"] = storageLoc.id;

      console.log('Updating map: ' + mapname + " " + modtype + ", key: " + map_key + ", value: " + map_value);

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

             console.log('Map updated.');
             toastr.success('Map content updated!');
             //$scope.reloadStorageObjects();
           } else {
             console.log("Failure status returned by: " + modtype + "mapentry");
             $scope.errorMessage = "An error occured while saving your object.";
             if (viewMapModalVisible) {
               $uibModal.open({
                 animation: true,
                 scope: $scope,
                 templateUrl: 'app/pages/workflows/modals/errorModal.html',
                 size: 'md',
               });
             }
           }
       }, function errorCallback(response) {
           console.log("Error occurred during " + modtype + "mapentry");
           console.log(response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (viewMapModalVisible) {
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
