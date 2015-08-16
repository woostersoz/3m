(function () {
  'use strict';

  angular
    .module('mmm.authentication', [
      'mmm.authentication.controllers',
      'mmm.authentication.services',
      'mmm.authentication.directives'
    ]);

  angular
    .module('mmm.authentication.controllers', []);

  angular
    .module('mmm.authentication.services', ['ngCookies']);
  
  angular
  .module('mmm.authentication.directives', ['ngTouch']);
})();