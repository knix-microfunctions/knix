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

  angular.module('MfnWebConsole.pages.storage')
    .controller('StorageTableCtrl', StorageTableCtrl);

  /** @ngInject */
  function StorageTableCtrl($scope, $http, $cookies, $filter, editableOptions, editableThemes, $uibModal, baProgressModal, toastr, sharedProperties, sharedData) {

    $scope.storageLocations = {};
    $scope.bucketTables = {};
    var defaultTable = "defaultTable";

    $scope.storageLocations = [
      { name: 'General Storage', type: 'Default Bucket', id: '' }
    ];

    $scope.storageLocations.selected = { name: "General Storage", type: "Default Bucket", id: '' };

    $scope.itemsByPage = 10;

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    var token = $cookies.get('token');
    var email = $cookies.get('email');
    var urlPath = sharedProperties.getUrlPath();
    var storageLoc = sharedProperties.getStorageLocation();

    $scope.workflows = sharedData.getWorkflows();

    getBucketList();

    function getWorkflows() {

      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
          'Content-Type': 'application/json'
        },
        data: JSON.stringify({ "action": "getWorkflows", "data": { "user": { "token": token } } })
      }

      $http(req).then(function successCallback(response) {

        if (response.data.status == "success") {

          $scope.workflows = response.data.data.workflows;
          sharedData.setWorkflows(response.data.data.workflows);
          for (var i = 0; i < $scope.workflows.length; i++) {
            $scope.storageLocations.push({ name: $scope.workflows[i].name, type: "Private Workflow Storage", id: $scope.workflows[i].id });
            if ($scope.workflows[i].id == storageLoc.id) {
              $scope.storageLocations.selected = { name: $scope.workflows[i].name, type: "Private Workflow Storage" };
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


    //$scope.storageObjects = sharedData.getStorageObjects();
    if (!$scope.storageObjects) {
      $scope.storageObjects = [];
    }
    getStorageObjectsList();
    //}

    $scope.open = function (page, size, key, message) {
      sharedProperties.setObjectKey(key);
      $scope.errorMessage = message;
      $uibModal.open({
        animation: true,
        scope: $scope,
        backdrop: 'static',
        keyboard: false,
        templateUrl: page,
        size: size,
      });

    };

    $scope.onSelected = function (selectedItem) {
      storageLoc = selectedItem;
      sharedProperties.setStorageLocation(storageLoc);
      getStorageObjectsList();
    }

    function getBucketList() {

      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
          'Content-Type': 'application/json'
        },

        data: JSON.stringify({ "action": "getTriggerableBuckets", "data": { "user": { "token": token } } })
      }

      $http(req).then(function successCallback(response) {

        if (response.data.status == "success") {
          $scope.bucketTables = Object.keys(response.data.data.buckets);
          for (var i = 0; i < $scope.bucketTables.length; i++) {
            $scope.storageLocations.push({ name: $scope.bucketTables[i], type: "Bucket", id: "" });
            if ($scope.bucketTables[i] == storageLoc.name) {
              $scope.storageLocations.selected = { name: $scope.bucketTables[i], type: "Bucket", id: "" };
            }
          }
          if (!$scope.workflows) {
            getWorkflows();
          } else {
            for (var i = 0; i < $scope.workflows.length; i++) {
              $scope.storageLocations.push({ name: $scope.workflows[i].name, type: "Private Workflow Storage", id: $scope.workflows[i].id });
              if ($scope.workflows[i].id == storageLoc.id) {
                $scope.storageLocations.selected = { name: $scope.workflows[i].name, type: "Private Workflow Storage", id: $scope.workflows[i].id };
              }
            }
          }

        } else {
          console.log("Failure status returned by getTriggerableBuckets action");
          console.log("Message:" + response.data);
          $scope.errorMessage = "An error occurred while attempting to retrieve the list of storage trigger tables.";
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });
        }


      }, function errorCallback(response) {
        console.log("Error occurred during getTriggerableBuckets action");
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


    function getStorageObjectsList() {

      var table = "";
      if (storageLoc.type == "Bucket") {
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
        data: JSON.stringify({ "action": "performStorageAction", "data": { "user": { "token": token }, "storage": { "action": "listkeys", "start": 0, "count": 2000, "tableName": table, "workflowid": storageLoc.id } } })
      }

      $http(req).then(function successCallback(response) {
        if (response.data.status == "success") {
          $scope.storageObjects = [];
          for (var i = 0; i < response.data.data.keylist.length; i++) {
            if (!response.data.data.keylist[i].startsWith("grain_requirements_") && !response.data.data.keylist[i].startsWith("grain_source_") && !response.data.data.keylist[i].startsWith("workflow_json_") && !response.data.data.keylist[i].endsWith("_metadata")) {
              $scope.storageObjects.push({ "key": response.data.data.keylist[i], "modified": "Z" });
            }
          }
          //sharedData.setStorageObjects($scope.storageObjects);

        } else {
          console.log("Failure status returned by performStorageAction / listKeys");
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
        console.log("Error occurred during listKeys action");
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

    $scope.getIndex = function (storageObject) {
      return $scope.storageObjects.indexOf(storageObject);
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



    $scope.downloadStorageObject = function (key) {
      console.log('retrieving storage object ' + key);
      toastr.success('Your object is being downloaded');

      var table = "";
      if (storageLoc.type == "Bucket") {
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
        data: JSON.stringify({ "action": "performStorageAction", "data": { "user": { "token": token }, "storage": { "action": "getdata", "key": key, "tableName": table, "workflowid": storageLoc.id } } })
      }

      $http(req).then(function successCallback(response) {

        if (response.data.status == "success") {
          var objectData = response.data.data.value;

          if (objectData != "") {
            console.log('Storage object sucessfully retrieved.');

            var binaryString = "";
            var blob = "";
            try {
              binaryString = window.atob(objectData);

              var binaryLen = binaryString.length;
              var bytes = new Uint8Array(binaryLen);
              for (var i = 0; i < binaryLen; i++) {
                var ascii = binaryString.charCodeAt(i);
                bytes[i] = ascii;
              }
              blob = new Blob([bytes]);
              var link = document.createElement('a');
              link.href = window.URL.createObjectURL(blob);
              var fileName = "";
              if (key.indexOf('.') == -1) {
                fileName = key + '.dat';
              } else {
                fileName = key;
              }
              link.download = fileName;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            } catch (e) {
              var element = document.createElement('a');
              element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(objectData));
              var fileName = "";
              if (key.indexOf('.') == -1) {
                fileName = key + '.dat';
              } else {
                fileName = key;
              }
              element.setAttribute('download', fileName);
              element.style.display = 'none';
              document.body.appendChild(element);
              element.click();
              document.body.removeChild(element);
            }
          }
        } else {
          console.log("getData action returned empty string");
          $scope.errorMessage = "The object does not contain any data.";
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });
        }
      }, function errorCallback(response) {
        console.log("Error occurred during getData action");
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


    $scope.deleteStorageObject = function (index) {
      console.log('deleting storage object ' + $scope.storageObjects[index].key);

      var table = "";
      if (storageLoc.type == "Bucket") {
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
        data: JSON.stringify({ "action": "performStorageAction", "data": { "user": { "token": token }, "storage": { "action": "deletedata", "key": $scope.storageObjects[index].key, "tableName": table, "workflowid": storageLoc.id } } })
      }

      $http(req).then(function successCallback(response) {

        if (response.data.status == "success") {
          console.log('Storage object sucessfully deleted.');
          toastr.success('Your object has been deleted successfully!');
          $scope.storageObjects.splice(index, 1);
        } else {
          console.log("Failure status returned by deleteData action");
          console.log(response.data);
          $scope.errorMessage = "An error occurred while attempting to delete the object.";
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });
        }
      }, function errorCallback(response) {
        console.log("Error occurred during deleteData action");
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

    $scope.removeStorageObject = function (index) {
      $scope.storageObjectToBeDeleted = $scope.storageObjects[index];
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/storage/modals/deleteStorageObjectModal.html',
        size: 'md',
      });


    };

    $scope.gotoPage = function (page) {

      angular
        .element($('#storageObjectPagination'))
        .isolateScope()
        .selectPage(page);

    }

    $scope.reloadStorageObjects = function () {
      getStorageObjectsList();
    }

    $scope.navigate = function (event, rowform, storageObject) {

      if (event.keyCode == 13) {
        rowform.$submit();
      }

    }

    // create new storage object
    $scope.createNewStorageObject = function (storageObject) {

      $scope.open('app/pages/storage/modals/uploadStorageObjectModal.html', 'lg', storageObject.key);

    };

    $scope.addStorageObject = function () {
      $scope.inserted = {
        key: '',
        modified: 'A'
      };
      $scope.storageObjects.push($scope.inserted);
      $scope.gotoPage(1);
    };

    editableOptions.theme = 'bs3';
    editableThemes['bs3'].submitTpl = '<button type="submit" class="btn btn-primary btn-with-icon"><i class="ion-checkmark-round"></i></button>';
    editableThemes['bs3'].cancelTpl = '<button type="button" ng-click="$form.$cancel()" class="btn btn-default btn-with-icon"><i class="ion-close-round"></i></button>';


  }

})();
