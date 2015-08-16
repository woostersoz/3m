(function () {
  'use strict';

  angular
    .module('mmm.authentication', [
      'mmm.authentication.controllers',
      'mmm.authentication.services'
    ]);

  angular
    .module('mmm.authentication.controllers', []);

  angular
    .module('mmm.authentication.services', ['ngCookies']);
})();