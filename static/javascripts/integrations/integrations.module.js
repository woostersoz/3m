(function () {
  'use strict';

  angular
    .module('mmm.integrations', [
      'mmm.integrations.controllers',
      'mmm.integrations.directives',
      'mmm.integrations.services',
    ]);

  angular
    .module('mmm.integrations.controllers', ['datatables']);

  angular
    .module('mmm.integrations.directives', []);

  angular
    .module('mmm.integrations.services', []);

})();