(function () {
  'use strict';

  angular
  .module('mmm', [
    'mmm.config',
    'mmm.routes',
    'mmm.filters',
    'mmm.authentication',
    'mmm.layout',
    'mmm.utils',
    'mmm.profiles',
    'mmm.leads',
    'mmm.campaigns',
    'mmm.integrations',
  ]);

  angular
    .module('mmm.routes', ['ngRoute']);
  angular
    .module('mmm.config', []);
  angular
  .module('mmm.filters', []);
  angular
    .module('mmm')
    .run(run);

  run.$inject = ['$http'];

/**
* @name run
* @desc Update xsrf $http headers to align with Django's defaults
*/
function run($http) {
  $http.defaults.xsrfHeaderName = 'X-CSRFToken';
  $http.defaults.xsrfCookieName = 'csrftoken';
}
})();