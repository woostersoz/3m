(function () {
  'use strict';

  angular
    .module('mmm.campaigns', [
      'mmm.campaigns.controllers',
//      'mmm.campaigns.directives',
      'mmm.campaigns.services',
      'ngDialog',
    ]);

  angular
    .module('mmm.campaigns.controllers', ['datatables']);

/*  angular
    .module('mmm.campaigns.directives', ['ngDialog']);*/

  angular
    .module('mmm.campaigns.services', []);

})();