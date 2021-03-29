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
  angular.module('MfnWebConsole').controller('UploadObjectCtrl', function($scope, $http, $cookies, $timeout, $uibModal, toastr, sharedProperties) {

    var token = $cookies.get('token');
    var email = $cookies.get('email');
    var uploadStorageObjectModalVisible = true;
    var defaultTable = "defaultTable";
    var urlPath = sharedProperties.getUrlPath();
    var storageLoc = sharedProperties.getStorageLocation();


     $scope.file_changed = function(element) {
       var file = element.files[0];

      uploadStatus = "Uploading <b>" + file.name + "</b>...";
      document.getElementById("uploadStatus").innerHTML = uploadStatus;
      $scope.progressBar = 0;
      $scope.progressCounter = $scope.progressBar;
      document.getElementById("progBar").style.display = 'inline';

      var reader = new FileReader();

      reader.onload = function(e){
        $scope.$apply(function(){

          var fileContents = reader.result.slice(reader.result.indexOf("base64,") + "base64,".length);

          //var tte = atob(fileContents);
          $scope.uploadFile(fileContents, file.name, fileContents.length);

        });
      };
      reader.readAsDataURL(file);

     };

     $scope.getKey = function() {
       return sharedProperties.getObjectKey();
     }

     $scope.aceLoaded = function(_editor) {

       $scope.aceSession = _editor.getSession();
       $scope.aceCodeEditor = _editor;
       _editor.$blockScrolling = Infinity;
       _editor.focus();

       console.log('Loading object:' + sharedProperties.getObjectKey());

       var table = "";
       if (storageLoc.type=="Bucket") {
        table = storageLoc.name;
       } else {
         table = defaultTable;
       }

       var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : { "data_type": "kv", "parameters": { "action": "getdata", "key": sharedProperties.getObjectKey(), "tableName" : table}, "workflowid" :  storageLoc.id} } })
       }

       $http(req).then(function successCallback(response) {

          if (response.data.status == "success")
          {
            console.log('Storage object successfully downloaded.');
            var objectData = response.data.data.value;
            if (objectData) {
              if (objectData.length<10000) {
                _editor.getSession().setValue(objectData);
              } else {
                _editor.getSession().setValue('Storage object data is too large to display inline. Please download the object instead.');
              }
            }
            _editor.focus();
          }
       }, function errorCallback(response) {
           console.log("Error occurred during getData");
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (uploadStorageObjectModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     };

     function isASCII(str) {
      return /^[\x00-\x7F]*$/.test(str);
     }


     $scope.setFocus = function() {
       $timeout(function() {
         $scope.aceCodeEditor.focus();
       }, 350);

     }

     $scope.$on('$destroy', function(){
         uploadStorageObjectModalVisible = false;
     });

     $scope.saveChanges = function() {

       var objectData = $scope.aceSession.getDocument().getValue();
       var dataStr = "";
       if (objectData=="Storage object data is too large to display inline. Please download the object instead."
       || objectData=="Storage object contains non-ASCII characters. Please download the object instead.") {
         return;
       }

       if (!isASCII(objectData))
       {
           dataStr = btoa(objectData);
       }
       else
       {
          dataStr = objectData;
       }

       var table = "";
       if (storageLoc.type=="Bucket") {
        table = storageLoc.name;
       } else {
         table = defaultTable;
       }

      var req = {
         method: 'POST',
         url: urlPath,
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : { "data_type": "kv", "parameters": { "action": "putdata", "key": sharedProperties.getObjectKey(), "value": dataStr, "tableName" : table}, "workflowid" :  storageLoc.id} } })
       }

       $http(req).then(function successCallback(response) {

         if (response.data.status=="success") {

             console.log('Object successfully uploaded.');
             toastr.success('Your object has been saved successfully!');
             //$scope.reloadStorageObjects();
           } else {
             console.log("Failure status returned by putData");
             $scope.errorMessage = "An error occured while saving your object.";
             if (uploadStorageObjectModalVisible) {
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
           if (uploadStorageObjectModalVisible) {
             $uibModal.open({
               animation: true,
               scope: $scope,
               templateUrl: 'app/pages/workflows/modals/errorModal.html',
               size: 'md',
             });
           }

       });
     };

     $scope.uploadFile = function(file, fileName, fileSize) {


       var encodedFile = file;
       var dataStr = "";

       try {
              var objectDataStr = atob(encodedFile);
              if (!isASCII(objectDataStr)) {
                dataStr = encodedFile;
              } else {
                dataStr = objectDataStr;
              }
            } catch(e) {
                dataStr = encodedFile;
            }
            
            var table = "";
            if (storageLoc.type=="Bucket") {
             table = storageLoc.name;
            } else {
              table = defaultTable;
            }
       var req = {
         method: 'POST',
         url: urlPath,
         uploadEventHandlers: {
           progress: function (e) {
               if (e.lengthComputable) {
                  $scope.progressBar = Math.floor(((e.loaded) / dataStr.length) * 100);
                  $scope.progressCounter = $scope.progressBar;
               }
             }
         },
         headers: {
           'Content-Type': 'application/json'
         },
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : { "data_type": "kv", "parameters": { "action": "putdata", "key": sharedProperties.getObjectKey(), "value": dataStr, "tableName" : table}, "workflowid" :  storageLoc.id} } })
       }

       $http(req).then(function successCallback(response) {

         if (response.data.status=="success") {

             console.log('Object sucessfully uploaded.');
             toastr.success('Your object has been uploaded successfully!');

             uploadStatus = "Last uploaded file: <b>" + fileName + "</b>";

             document.getElementById("progBar").style.display = 'none';
             $scope.progressBar = 0;
             $scope.progressCounter = $scope.progressBar;

             if (encodedFile.length<10000) {
              try {
                if (!isASCII(atob(encodedFile))) {
                  $scope.aceSession.setValue('Storage object contains non-ASCII characters. Please download the object instead.');
                } else {
                  $scope.aceSession.setValue(atob(encodedFile));
                }
              } catch(e) {
                $scope.aceSession.setValue(encodedFile);
              }
            } else {
              $scope.aceSession.setValue('Storage object data is too large to display inline. Please download the object instead.');
            }

           } else {
             console.log("Failure status returned by putData");
             $scope.errorMessage = "An error occured while uploading your object.";
             if (uploadStorageObjectModalVisible) {
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
           console.log("Response:" + response);
           if (response.statusText) {
             $scope.errorMessage = response.statusText;
           } else {
             $scope.errorMessage = response;
           }
           if (uploadStorageObjectModalVisible) {
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
