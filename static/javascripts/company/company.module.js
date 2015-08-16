(function () {
  'use strict';

  angular
    .module('mmm.company', [
      'mmm.company.controllers',
      //'mmm.company.directives',
      'mmm.company.services',
    ]);

  angular
    .module('mmm.company.controllers', ['datatables']);

  /*angular
    .module('mmm.company.directives', ['ngDialog']);*/

  angular
    .module('mmm.company.services', []);

})();