(function () {
  'use strict';

  angular
    .module('mmm.dashboards', [
      'mmm.dashboards.controllers',
      'mmm.dashboards.services',
    ]);

  angular
    .module('mmm.dashboards.controllers', ['datatables']);

  angular
    .module('mmm.dashboards.services', []);

})();