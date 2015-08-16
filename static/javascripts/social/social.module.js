(function () {
  'use strict';

  angular
    .module('mmm.social', [
      'mmm.social.controllers',
//      'mmm.social.directives',
      'mmm.social.services',
    ]);

  angular
    .module('mmm.social.controllers', ['datatables']);

/*  angular
    .module('mmm.social.directives', ['ngDialog']);*/

  angular
    .module('mmm.social.services', []);

})();