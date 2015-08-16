(function () {
  'use strict';

  angular
    .module('mmm.binders', [
      'mmm.binders.controllers',
//      'mmm.leads.directives',
      'mmm.binders.services'
    ]);

  angular
    .module('mmm.binders.controllers', ['datatables']);

  angular
    .module('mmm.binders.directives', []);

  angular
    .module('mmm.binders.services', []);

})();