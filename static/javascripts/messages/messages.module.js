(function () {
  'use strict';

  angular
    .module('mmm.messages', [
      'mmm.messages.controllers',
      'mmm.messages.directives',
      'mmm.messages.services',
    ]);

  angular
    .module('mmm.messages.controllers', ['datatables']);

  angular
    .module('mmm.messages.directives', []);

  angular
    .module('mmm.messages.services', []);

})();