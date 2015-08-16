(function () {
  'use strict';

  angular
    .module('mmm.snapshots', [
      'mmm.snapshots.controllers',
//      'mmm.leads.directives',
      'mmm.snapshots.services',
    ]);

  angular
    .module('mmm.snapshots.controllers', ['datatables']);

/*  angular
    .module('mmm.leads.directives', ['ngDialog']);*/

  angular
    .module('mmm.snapshots.services', []);

})();