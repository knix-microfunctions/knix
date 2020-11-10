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

  angular.module('MfnWebConsole.pages.storage', [ 'ui.select', 'ngSanitize' ])
      .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {

    $stateProvider
      .state('storage', {
         url: '/storage',
         template : '<ui-view autoscroll="true" autoscroll-body-top></ui-view>',
         abstract: true,
         title: 'Object Store',
         sidebarMeta: {
           icon: 'ion-compose',
           order: 250,
         },
      })
      .state('storage.kv', {
         url: '/kv',
         templateUrl: 'app/pages/storage/smart/tables.html',
         title: 'Keys-Values',
         controller: 'StorageTableCtrl',
         sidebarMeta: {
           order: 0,
         },
       })
      .state('storage.maps', {
         url: '/maps',
         templateUrl: 'app/pages/storage/smart/maps.html',
         title: 'CRDT Maps',
         controller: 'StorageTableCtrl',
         sidebarMeta: {
           order: 100,
         },
       })
      .state('storage.sets', {
         url: '/sets',
         templateUrl: 'app/pages/storage/smart/sets.html',
         title: 'CRDT Sets',
         controller: 'StorageTableCtrl',
         sidebarMeta: {
           order: 200,
         },
       })
      .state('storage.counters', {
         url: '/counters',
         templateUrl: 'app/pages/storage/smart/counters.html',
         title: 'CRDT Counters',
         controller: 'StorageTableCtrl',
         sidebarMeta: {
           order: 300,
         },
       })
       .state('storage.bucketList', {
          url: '/bucketList',
          templateUrl: 'app/pages/storage/smart/buckets.html',
          title: 'Triggerable Buckets',
          controller: 'BucketListCtrl',
          sidebarMeta: {
              order: 400,
          },

      })
  }

})();
