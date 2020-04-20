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

  angular.module('MfnWebConsole.pages.docs', [

  ])
      .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {

    /** @ngInject */
    $stateProvider
      .state('docs', {
        url: '/docs',
        template : '<ui-view autoscroll="true" autoscroll-body-top></ui-view>',
        abstract: true,
        title: 'Documentation',
        sidebarMeta: {
          icon: 'ion-compose',
          order: 250,
        },
      })
      .state('docs.intro', {
         url: '/intro',
         templateUrl: 'app/pages/docs/intro/intro.html',
         title: 'Getting Started',
         sidebarMeta: {
           order: 0,
         },
       })
       .state('docs.usecases', {
         url: '/usecases',
         templateUrl: 'app/pages/docs/usecases/usecases.html',
         title: 'Use Cases',
         sidebarMeta: {
           order: 100,
         },
       })
       .state('docs.python_api', {
          url: '/python_api',
          templateUrl: 'app/pages/docs/api/python_api.html',
          title: 'Python API',
          sidebarMeta: {
            order: 300,
          },
       })
       .state('docs.java_api', {
        url: '/java_api',
        templateUrl: 'app/pages/docs/api/java_api.html',
        title: 'Java API',
        sidebarMeta: {
          order: 350,
        },
       })
       .state('docs.sdk', {
          url: '/sdk',
          templateUrl: 'app/pages/docs/sdk/sdk.html',
          title: 'SDK',
          sidebarMeta: {
            order: 400,
          },
       })
       .state('docs.faqs', {
         url: '/faqs',
         templateUrl: 'app/pages/docs/faqs/faqs.html',
         title: 'FAQs',
         sidebarMeta: {
           order: 400,
         },
       });

     }
   })();
