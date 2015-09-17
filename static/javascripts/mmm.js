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
    'mmm.dashboards',
    'mmm.binders',
    'mmm.accounts',
    'mmm.superadmin',
    'mmm.social',
    'mmm.websites',
    'mmm.common',
    'ng.django.forms',
    'ngTouch', 
    //'slick',
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
    'angular.filter',
    'nemLogging',
    'leaflet-directive',
    'ncy-angular-breadcrumb'
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

  run.$inject = ['$http', '$rootScope', 'editableOptions', '$state'];

/**
* @name run
* @desc Update xsrf $http headers to align with Django's defaults
*/
function run($http, $rootScope, editableOptions, $state) {
  $http.defaults.xsrfHeaderName = 'X-CSRFToken';
  $http.defaults.xsrfCookieName = 'csrftoken';
  $rootScope.$on("$stateChangeError", console.log.bind(console));
  editableOptions.theme = 'bs3';
  
  $rootScope.htmlReady = function() {
	    $rootScope.$evalAsync(function() {
	      setTimeout(function() {
	        var evt = document.createEvent('Event');
	        evt.initEvent('_htmlReady', true, true);
	        document.dispatchEvent(evt);
	      }, 0);
	    });
  };
  
  $rootScope.$on('$stateChangeStart', function(event, toState, toParams, fromState) {
  	if (toState.redirectTo) {
  		event.preventDefault();
  		$state.go(toState.redirectTo, toParams);
  	}
  });
  
}
})();