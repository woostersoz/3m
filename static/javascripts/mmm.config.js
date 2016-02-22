(function () {
  'use strict';

  angular
    .module('mmm.config')
    .config(config);

  config.$inject = ['$locationProvider', '$httpProvider', '$injector'];
 
  /**
  * @name config
  * @desc Enable HTML5 routing
  */
  function config($locationProvider, $httpProvider, $injector, usSpinnerConfigProvider) {
    $locationProvider.html5Mode(true);
    $locationProvider.hashPrefix('!');
    

    //usSpinnerConfigProvider.setDefaults({'color': '#bedb39'});
    //$httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
    $httpProvider.defaults.headers.common['X-CSRFToken'] = '{% csrf_value %}';
    
    
    /*$httpProvider.interceptors.push(function($q, $injector) {
       return {
    	'response': function(response) {
            var $http = $http || $injector.get('$http');
            var $timeout = $injector.get('$timeout');
            var $rootScope = $injector.get('$rootScope');
            if($http.pendingRequests.length < 1) {
                $timeout(function(){
                    if($http.pendingRequests.length < 1){
                        $rootScope.htmlReady();
                    }
                }, 700);//an 0.7 seconds safety interval, if there are no requests for 0.7 seconds, it means that the app is through rendering
            }
            return response;
        },

        'responseError': function(rejection) {
            $http = $http || $injector.get('$http');

            return $q.reject(rejection);
        }
      };
    });    */
    
   
  }
})();