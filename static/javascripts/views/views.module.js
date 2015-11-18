(function () {
  'use strict';

  angular
    .module('mmm.views', [
      'mmm.views.controllers',
      'mmm.views.services',
    ]);

  angular
    .module('mmm.views.controllers', ['datatables']);

  angular
    .module('mmm.views.services', []);

})();