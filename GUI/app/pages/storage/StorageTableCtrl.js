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
    $scope.dataType = "kv";

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    var token = $cookies.get('token');
    var email = $cookies.get('email');
    var urlPath = sharedProperties.getUrlPath();
    var storageLoc = sharedProperties.getStorageLocation();
    var storage_data_types = ["kv", "map", "set", "counter"];

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

    for (var i = 0; i < storage_data_types.length; i++)
    {
        resetScopeStorageObjects(storage_data_types[i]);
        getStorageObjectsList(storage_data_types[i]);
    }

    function resetScopeStorageObjects(data_type)
    {
        if (data_type == "kv")
        {
            $scope.storageObjects = [];
        }
        else if (data_type == "map")
        {
            $scope.storageObjectsMaps = [];
        }
        else if (data_type == "set")
        {
            $scope.storageObjectsSets = [];
        }
        else if (data_type == "counter")
        {
            $scope.storageObjectsCounters = [];
        }
    }

    function getScopeStorageObjects(data_type) {
        if (data_type == "kv")
        {
            return $scope.storageObjects;
        }
        else if (data_type == "map")
        {
            return $scope.storageObjectsMaps;
        }
        else if (data_type == "set")
        {
            return $scope.storageObjectsSets;
        }
        else if (data_type == "counter")
        {
            return $scope.storageObjectsCounters;
        }
    }

    $scope.open = function (page, size, key, message, data_type) {
        if (data_type == "map")
        {
            sharedProperties.setMapName(key);
        }
        else if (data_type == "set")
        {
            sharedProperties.setSetName(key);
        }
        else if (data_type == "counter")
        {
            sharedProperties.setCounterName(key);
        }
        else
        {
            sharedProperties.setObjectKey(key);
        }
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

    $scope.onSelected = function (selectedItem, data_type) {
        storageLoc = selectedItem;
        sharedProperties.setStorageLocation(storageLoc);
        getStorageObjectsList(data_type);
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

    function getStorageObjectsList(data_type) {
      var storageLoc = sharedProperties.getStorageLocation();
      var table = "";
      if (storageLoc.type == "Bucket") {
        table = storageLoc.name;
      } else {
        table = defaultTable;
      }
            
      var param_storage = {};
      param_storage["data_type"] = data_type;
      param_storage["parameters"] = {};
      if (data_type == "kv")
      {
          param_storage["parameters"]["action"] = "listkeys";
          param_storage["parameters"]["tableName"] = table;
      }
      else
      {
          param_storage["parameters"]["action"] = "list" + data_type + "s";
      }
      param_storage["parameters"]["start"] = 0;
      param_storage["parameters"]["count"] = 2000;
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
        if (response.data.status == "success") {
              resetScopeStorageObjects(data_type);
              var storageObjects = getScopeStorageObjects(data_type);

              if (data_type == "kv")
              {
                  for (var i=0;i<response.data.data.keylist.length;i++) {
                      if (!response.data.data.keylist[i].includes("_branch_")) {
                        storageObjects.push({"key" : response.data.data.keylist[i], "modified" : "Z", "selected" : false});
                      }
                  }
              }
              else
              {
                  var data_type_list = data_type + "list"
                  for (var i=0;i<response.data.data[data_type_list].length;i++) {
                      var so = {"key" : response.data.data[data_type_list][i], "modified" : "Z"};
                      storageObjects.push(so);
                  }
              }
          //sharedData.setStorageObjects($scope.storageObjects);

        } else {
          console.log("Failure status returned by performStorageAction / " + param_storage["parameters"]["action"]);
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
        console.log("Error occurred during action: " + param_storage["parameters"]["action"]);
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

    $scope.getStorageObjectKey = function(storageObject, data_type)
    {
        var idx = $scope.getIndex(storageObject, data_type);
        var storageObjects = getScopeStorageObjects(data_type);
        return storageObjects[idx].key;
    }

    $scope.getIndex = function(storageObject, data_type) {
        var storageObjects = getScopeStorageObjects(data_type);
        return storageObjects.indexOf(storageObject);
    }

    function dateFormat(d) {
      var format = "d-m-Y H:i:s";
      return format

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
         data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : { "data_type": "kv", "parameters": { "action": "getdata", "key": key, "tableName": table }, "workflowid" :  storageLoc.id} } })
       }

       $http(req).then(function successCallback(response) {

        if (response.data.status == "success") {
          var objectData = response.data.data.value;

          if (objectData != "") {
            console.log('Storage object successfully retrieved.');

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


    $scope.deleteStorageObject = function(key, dataType) {

      var storageLoc = sharedProperties.getStorageLocation();
      console.log('deleting storage object ' + key);

      var table = "";
      if (storageLoc.type == "Bucket") {
        table = storageLoc.name;
      } else {
        table = defaultTable;
      }

      var param_storage = {};
      
      param_storage["data_type"] = dataType;
      param_storage["parameters"] = {};
      if (dataType == "kv")
      {
          param_storage["parameters"]["action"] = "deletedata";
          param_storage["parameters"]["key"] = key;
          param_storage["parameters"]["tableName"] = table;
      }
      else
      {
          param_storage["parameters"]["action"] = "delete" + dataType;
          param_storage["parameters"][dataType + "name"] = key;
      }
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

        if (response.data.status == "success") {
          console.log('Storage object successfully deleted.');
          toastr.success('Your object has been deleted successfully!');
          
        } else {
          console.log("Failure status returned by performStorageAction / " + param_storage["parameters"]["action"]);
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

    $scope.clearStorageObject = function(index, data_type) {
      var scopeStorageObjects = getScopeStorageObjects(data_type);
      var param_storage = {};
      param_storage["data_type"] = data_type;
      param_storage["parameters"] = {};
      param_storage["parameters"]["action"] = "clear" + data_type;
      param_storage["parameters"][data_type + "name"] = scopeStorageObjects[index].key;
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
            console.log('Storage object successfully cleared.');
            toastr.success('Your object has been cleared successfully!');
          } else {
            console.log("Failure status returned by clear action");
            console.log(response.data);
            $scope.errorMessage = "An error occurred while attempting to clear the object.";
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
      }, function errorCallback(response) {
          console.log("Error occurred during action: " + param_storage["parameters"]["action"]);
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

    $scope.clearStorageObjectPrep = function(index, data_type) {
      var scopeStorageObjects = getScopeStorageObjects(data_type);
      $scope.storageObjectToBeCleared = scopeStorageObjects[index];
      $scope.storageObjectToBeCleared.data_type = data_type;
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/storage/modals/clearStorageObjectModal.html',
        size: 'md',
      });


    };

    $scope.removeStorageObject = function(index, data_type) {
      var scopeStorageObjects = getScopeStorageObjects(data_type);
      $scope.storageObjectToBeDeleted = scopeStorageObjects[index];
      $scope.storageObjectToBeDeleted.data_type = data_type;
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/storage/modals/deleteStorageObjectModal.html',
        size: 'md',
      });
    };

    $scope.removeMultipleStorageObjects = function(dataType) {
      var storageObjects = getScopeStorageObjects(dataType);
      $scope.storageObjectsToBeDeleted = "";
      $scope.dataType = dataType
      for (var i = 0; i < storageObjects.length; i++) {
        if (storageObjects[i].selected) {
          if ($scope.storageObjectsToBeDeleted!="") {
            $scope.storageObjectsToBeDeleted += ", ";
          }
          $scope.storageObjectsToBeDeleted += storageObjects[i].key;
        }
      }
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/storage/modals/deleteMultipleStorageObjectsModal.html',
        size: 'md',
      });
    };

    $scope.gotoPage = function (page) {

      angular
        .element($('#storageObjectPagination'))
        .isolateScope()
        .selectPage(page);

    }

    $scope.reloadStorageObjects = function(data_type) {
        getStorageObjectsList(data_type);
    }

    $scope.navigate = function (event, rowform, storageObject) {

      if (event.keyCode == 13) {
        rowform.$submit();
      }

    }

    function forceStorageObjectCreationInBackground(name, data_type)
    {
        if (data_type != "map" && data_type != "set")
        {
            return;
        }

        // first, create a dummy entry
        var param_storage = {};
        param_storage["data_type"] = data_type;
        param_storage["parameters"] = {};
        param_storage["parameters"][data_type + "name"] = name;
        if (data_type == "map")
        {
            param_storage["parameters"]["action"] = "putmapentry";
            param_storage["parameters"]["key"] = name;
            param_storage["parameters"]["value"] = "";
        }
        else if (data_type == "set")
        {
            param_storage["parameters"]["action"] = "addsetentry";
            param_storage["parameters"]["item"] = "";
        }
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
            console.log('Storage object successfully created (background).');
                // then, clear
                param_storage["parameters"]["action"] = "clear" + data_type;
                if (data_type == "map")
                {
                    delete param_storage["parameters"]["key"];
                    delete param_storage["parameters"]["value"];
                }
                else if (data_type == "set")
                {
                    delete param_storage["parameters"]["item"];
                }

                var req2 = {
                 method: 'POST',
                 url: urlPath,
                 headers: {
                   'Content-Type': 'application/json'
                 },
                 data:  JSON.stringify({ "action" : "performStorageAction", "data" : { "user" : { "token" : token } , "storage" : param_storage } })
                }

                $http(req2).then(function successCallback(response) {
                  if (response.data.status=="success") {
                    console.log('Storage object successfully cleared (background).');
                    $scope.reloadStorageObjects(data_type);
                  } else {
                    console.log("Failure status returned by action (background)");
                    console.log(response.data);
                  }
                }, function errorCallback(response) {
                  console.log("Error occurred during action (background)");
                  console.log("Response:" + response);
                });

            $scope.reloadStorageObjects(data_type);
          } else {
            console.log("Failure status returned by action (background)");
            console.log(response.data);
          }
        }, function errorCallback(response) {
          console.log("Error occurred during action (background)");
          console.log("Response:" + response);
        });

    }

    $scope.downloadSelected = function() {
      
      for (var i = 0; i < $scope.storageObjects.length; i++) {
        if ($scope.storageObjects[i].selected) {
           $scope.downloadStorageObject($scope.storageObjects[i].key);
        }
      }
    }

    $scope.selectAll = function(dataType) {
      
      var storageObjects = getScopeStorageObjects(dataType);
      if (document.getElementById(dataType + "ObjectsSelectAll").checked) {
        for (var i = 0; i < storageObjects.length; i++) {
          storageObjects[i].selected = true;
        }
      } else {
        for (var i = 0; i < storageObjects.length; i++) {
          storageObjects[i].selected = false;
        }
      }
    }

    $scope.spliceStorageObject = function(storageObject, dataType) {

      var storageObjects = getScopeStorageObjects(dataType);
      storageObjects.splice($scope.getIndex(storageObject, dataType), 1);

    };

    $scope.deleteSelected = function() {

      var storageObjects = getScopeStorageObjects($scope.dataType);
      var objectsToBeDeleted = [];
      for (var i = 0; i < storageObjects.length; i++) {
        if (storageObjects[i].selected) {
          objectsToBeDeleted.push({key: storageObjects[i].key});
        }
      }
      for (var i = 0; i < objectsToBeDeleted.length; i++) {
        for (var t = 0; t < storageObjects.length; t++) {
          if (storageObjects[t].key==objectsToBeDeleted[i].key) {
            storageObjects.splice(t, 1);
          }
        }
        $scope.deleteStorageObject(objectsToBeDeleted[i].key, $scope.dataType);
      }
    }


    // create new storage object
    $scope.createNewStorageObject = function(storageObject, data_type) {
      var storageLoc = sharedProperties.getStorageLocation();

      if (storageObject.key!='')
      {
        console.log('creating new storage object ' + storageObject.key);
        if (data_type == "kv")
        {
            $scope.open('app/pages/storage/modals/uploadStorageObjectModal.html', 'lg', storageObject.key);
            return;
        }

        var param_storage = {};
        param_storage["data_type"] = data_type;
        param_storage["parameters"] = {};
        param_storage["parameters"]["action"] = "create" + data_type;
        param_storage["parameters"][data_type + "name"] = storageObject.key;
        if (data_type == "counter")
        {
            param_storage["parameters"][data_type + "value"] = 0;
        }
      
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
            // add a dummy entry to force creation of the map/set and then clear it
            forceStorageObjectCreationInBackground(storageObject.key, data_type);

            console.log('Storage object successfully created.');
            toastr.success('Your object has been created successfully!');
            $scope.reloadStorageObjects(data_type);
            //$scope.open('app/pages/storage/modals/uploadStorageObjectModal.html', 'lg', storageObject.key);

          } else {
            console.log("Failure status returned by save action");
            console.log(response.data);
            $scope.errorMessage = "An error occurred while attempting to create the object.";
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
        }, function errorCallback(response) {
          console.log("Error occurred during action: " + param_storage["parameters"]["action"]);
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

    $scope.addStorageObject = function(data_type) {
      var scopeStorageObjects = getScopeStorageObjects(data_type);
      $scope.inserted = {
        key: '',
        modified: 'A',
        selected: false
      };
      scopeStorageObjects.push($scope.inserted);
      $scope.gotoPage(1);
    };

    editableOptions.theme = 'bs3';
    editableThemes['bs3'].submitTpl = '<button type="submit" class="btn btn-primary btn-with-icon"><i class="ion-checkmark-round"></i></button>';
    editableThemes['bs3'].cancelTpl = '<button type="button" ng-click="$form.$cancel()" class="btn btn-default btn-with-icon"><i class="ion-close-round"></i></button>';


  }

})();
