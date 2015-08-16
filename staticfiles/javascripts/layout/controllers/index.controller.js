/**
* IndexController
* @namespace mmm.layout.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.layout.controllers')
    .controller('IndexController', IndexController);

  IndexController.$inject = ['$scope', 'Authentication', 'Snackbar', '$location'];

  /**
  * @namespace IndexController
  */
  function IndexController($scope, Authentication, Snackbar, $location) {
    var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
  

    activate();

    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.layout.controllers.IndexController
    */
    function activate() { 
      if (Authentication.getAuthenticatedAccount()) 
         var x = 1;
      else {
    	  Snackbar.error('You need to login first');
    	  $location.path('/login'); 
      }
      

      /**
      * @name symbolsSuccessFn
      * @desc Update symbols array on view
      */
      function portfolioitemsSuccessFn(data, status, headers, config) { 
        
      }


      /**
      * @name symbolsErrorFn
      * @desc Show snackbar with error
      */
      function portfolioitemsErrorFn(data, status, headers, config) {
        Snackbar.error(data.error);
      }
    }
  }
})();