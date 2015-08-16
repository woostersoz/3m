(function () {
  'use strict';

  angular
    .module('mmm.analytics', [
      'mmm.analytics.controllers',
      'mmm.analytics.services',
    ]);

  angular
    .module('mmm.analytics.controllers', ['datatables']);

  angular
    .module('mmm.analytics.services', []);

})();