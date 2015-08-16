(function () {
  'use strict';

  angular
    .module('mmm.superadmin', [
      'mmm.superadmin.controllers',
      'mmm.superadmin.directives',
      'mmm.superadmin.services',
    ]);

  angular
    .module('mmm.superadmin.controllers', ['datatables']);

  angular
    .module('mmm.superadmin.directives', []);

  angular
    .module('mmm.superadmin.services', []);

})();