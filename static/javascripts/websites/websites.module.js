(function () {
  'use strict';

  angular
    .module('mmm.websites', [
      'mmm.websites.controllers',
//      'mmm.websites.directives',
      'mmm.websites.services',
    ]);

  angular
    .module('mmm.websites.controllers', ['datatables']);

/*  angular
    .module('mmm.websites.directives', ['ngDialog']);*/

  angular
    .module('mmm.websites.services', []);

})();