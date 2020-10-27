/*   Copyright 2020 The microfunctions Authors

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
    .controller('BucketListCtrl', BucketListCtrl);

  /** @ngInject */
  function BucketListCtrl($scope, $http, $cookies, $window, $filter, editableOptions, editableThemes, $uibModal, baProgressModal, toastr, sharedProperties, sharedData) {

    $scope.itemsByPage = 10;
    $scope.entity = "Object Store";

    var token = $cookies.get('token');
    var storageEndpoint = $cookies.get('storageEndpoint');
    var urlPath = sharedProperties.getUrlPath();

    if (!$scope.bucketTables) {
      $scope.bucketTables = [];
    }
    getBucketList();

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
        } else {
          console.log("Failure status returned by getTriggerableBuckets action");
          console.log("Message:" + response.data);
          $scope.errorMessage = "An error occurred while attempting to retrieve the list of storage trigger buckets.";
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

    $scope.getIndex = function (bucket) {

      return $scope.bucketTables.indexOf(bucket);
    }

    $scope.deleteBucket = function (bucket) {
      console.log('deleting bucket table ' + $scope.bucketTables[bucket]);

      var req = {
        method: 'POST',
        url: urlPath,
        headers: {
          'Content-Type': 'application/json'
        },

        data: JSON.stringify({ "action": "deleteTriggerableBucket", "data": { "user": { "token": token }, "bucketname": $scope.bucketTables[bucket] } })
      }

      $http(req).then(function successCallback(response) {

        if (response.data.status == "success") {
          console.log('Bucket sucessfully deleted.');
          toastr.success('Your bucket has been deleted successfully!');
          $scope.bucketTables.splice(bucket, 1);
        } else {
          console.log("Failure status returned by deleteTriggerableBucket action");
          console.log("Message:" + response.data);
          $scope.errorMessage = "An error occurred while attempting to delete the bucket.";
          $uibModal.open({
            animation: true,
            scope: $scope,
            templateUrl: 'app/pages/workflows/modals/errorModal.html',
            size: 'md',
          });
        }
      }, function errorCallback(response) {
        console.log("Error occurred during deleteTriggerableBucket action");
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

    $scope.removeBucket = function (bucket) {
      $scope.bucketToBeDeleted = bucket;
      $uibModal.open({
        animation: true,
        scope: $scope,
        templateUrl: 'app/pages/storage/modals/deleteBucketModal.html',
        size: 'md',
      });
    };

    $scope.gotoPage = function (page) {

      angular
        .element($('#bucketPagination'))
        .isolateScope()
        .selectPage(page);

    }

    $scope.reloadBucketTables = function () {
      getBucketList();
    }

    $scope.navigate = function (event, rowform, bucket) {

      if (event.keyCode == 13) {
        rowform.$submit();
      }

    }

    $scope.setStorageLocation = function (bucket) {
      sharedProperties.setStorageLocation({ "name": bucket, "type": "Bucket", "id": "" });
      $window.location.href = '#/storage';
    };

    // create bucket table
    $scope.createBucket = function (bucket) {

      if (bucket != '') {
        console.log('creating new bucket ' + bucket);
        var req = {
          method: 'POST',
          url: urlPath,
          headers: {
            'Content-Type': 'application/json'
          },

          data: JSON.stringify({ "action": "addTriggerableBucket", "data": { "user": { "token": token }, "bucketname": bucket } })
        }


        $http(req).then(function successCallback(response) {
          if (response.data.status == "success") {
            console.log('Bucket sucessfully created.');
            toastr.success('Your bucket has been created successfully!');
            $scope.reloadBucketTables();
          } else {
            console.log("Failure status returned by addTriggerableBucket action");
            console.log("Message:" + response.data);
            $scope.errorMessage = "An error occurred while attempting to create the bucket.";
            $uibModal.open({
              animation: true,
              scope: $scope,
              templateUrl: 'app/pages/workflows/modals/errorModal.html',
              size: 'md',
            });
          }
        }, function errorCallback(response) {
          console.log("Error occurred during addTriggerableBucket action");
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

    $scope.addBucket = function () {
      $scope.inserted = "";
      $scope.bucketTables.push($scope.inserted);
      $scope.gotoPage(1);
    };

    editableOptions.theme = 'bs3';
    editableThemes['bs3'].submitTpl = '<button type="submit" class="btn btn-primary btn-with-icon"><i class="ion-checkmark-round"></i></button>';
    editableThemes['bs3'].cancelTpl = '<button type="button" ng-click="$form.$cancel()" class="btn btn-default btn-with-icon"><i class="ion-close-round"></i></button>';


  }

})();
