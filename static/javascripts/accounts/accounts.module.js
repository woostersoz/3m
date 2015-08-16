(function () {
  'use strict';

  angular
    .module('mmm.accounts', [
      'mmm.accounts.controllers',
//      'mmm.accounts.directives',
      'mmm.accounts.services',
    ]);

  angular
    .module('mmm.accounts.controllers', ['datatables']);

/*  angular
    .module('mmm.accounts.directives', ['ngDialog']);*/

  angular
    .module('mmm.accounts.services', []);

})();