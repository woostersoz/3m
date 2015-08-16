(function () {
  'use strict';

  angular
    .module('mmm.leads', [
      'mmm.leads.controllers',
//      'mmm.leads.directives',
      'mmm.leads.services',
    ]);

  angular
    .module('mmm.leads.controllers', ['datatables']);

/*  angular
    .module('mmm.leads.directives', ['ngDialog']);*/

  angular
    .module('mmm.leads.services', []);

})();