(function () {
  'use strict';

  angular
    .module('mmm.binders', [
      'mmm.binders.controllers',
      'mmm.binders.services',
      'mmm.analytics.services'
    ]);

  angular
    .module('mmm.binders.controllers', ['datatables' ]);

  angular
    .module('mmm.binders.directives', []);

  angular
    .module('mmm.binders.services', []);

})();