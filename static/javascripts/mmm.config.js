(function () {
  'use strict';

  angular
    .module('mmm.config')
    .config(config);

  config.$inject = ['$locationProvider', '$httpProvider'];
 
  /**
  * @name config
  * @desc Enable HTML5 routing
  */
  function config($locationProvider, $httpProvider, usSpinnerConfigProvider) {
    $locationProvider.html5Mode(true);
    $locationProvider.hashPrefix('!');
    
    //$httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
    $httpProvider.defaults.headers.common['X-CSRFToken'] = '{% csrf_value %}';
    
    
    
    
   
  }
})();