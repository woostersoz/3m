(function () {
  'use strict';
 
  angular
  .module('mmm', [
    'mmm.config',
//    'mmm.routes',
    'mmm.states',
    'mmm.filters',
    'mmm.authentication',
    'mmm.layout',
    'mmm.utils',
    'mmm.profiles',
    'mmm.leads',
    'mmm.campaigns',
    'mmm.integrations',
    'mmm.company',
    'mmm.analytics',
    'mmm.messages',
    'mmm.snapshots',
    'mmm.binders',
    'mmm.accounts',
    'mmm.superadmin',
    'mmm.social',
    'mmm.websites',
    'mmm.dashboards',
    'mmm.common',
    'ng.django.forms',
    'ngTouch', 
    'slick',
    'btford.socket-io',
    'nvd3',
    'daterangepicker',
    'ngAnimate',
    'angularMoment',
    'ui.bootstrap',
    'frapontillo.bootstrap-switch',
    'angularUtils.directives.dirPagination',
    'angularSpinner',
    'xeditable',
    'FBAngular',
    'angular.filter'
    
  ]);

  angular
    .module('mmm').constant('angularMomentConfig', {
    	preprocess: 'utc',
    	timezone: getLocalTimezone()
    });
/*  angular
    .module('mmm.routes', ['ngRoute']);*/
  angular
    .module('mmm.states', ['ui.router']);
  angular
    .module('mmm.config', []);
  angular
  .module('mmm.filters', []);
  angular
    .module('mmm')
    .run(run);

  run.$inject = ['$http', '$rootScope', 'editableOptions'];

/**
* @name run
* @desc Update xsrf $http headers to align with Django's defaults
*/
function run($http, $rootScope, editableOptions) {
  $http.defaults.xsrfHeaderName = 'X-CSRFToken';
  $http.defaults.xsrfCookieName = 'csrftoken';
  $rootScope.$on("$stateChangeError", console.log.bind(console));
  editableOptions.theme = 'bs3';
}
})();