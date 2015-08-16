/**
* Register controller
* @namespace mmm.authentication.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.authentication.controllers')
    .controller('RegisterController', RegisterController);

  RegisterController.$inject = ['$location', '$scope', 'Authentication', 'DTOptionsBuilder', 'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$state', '$stateParams',];

  /**
  * @namespace RegisterController
  */
  function RegisterController($location, $scope, Authentication, DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances, $state, $stateParams) {
    
	var vm = this;
    vm.users = [];
    vm.register = register;
    $scope.account = Authentication.getAuthenticatedAccount();
    
    if ($state.current.name == "users") {
    	if ($scope.account && $scope.account.is_admin) 
    		Authentication.getAllUsers($scope.account.company).then(getUsersSuccessFn, getUsersErrorFn);
    	else if (!$scope.account.is_admin)
    		toastr.error("Sorry, you need to be an admin!");
    }
    else {
    	activate();
    }
    

    function getUsersSuccessFn(data, status, headers, config) {
		if (data.data) {
			vm.users = data.data;
		}
	}

	function getUsersErrorFn(data, status, headers, config) {
		toastr.error("Could not retrieve users");
	}
    /**
     * @name activate
     * @desc Actions to be performed when this controller is instantiated
     * @memberOf thinkster.authentication.controllers.RegisterController
     */
    function activate() {
      // If the user is authenticated, they should not be here.
      if (Authentication.isAuthenticated()) {
        $location.url('/');
      }
    }
    
    /**
    * @name register
    * @desc Try to register a new user
    * @param {string} email The email entered by the user
    * @param {string} password The password entered by the user
    * @param {string} username The username entered by the user
    * @returns {Promise}
    * @memberOf thinkster.authentication.services.Authentication
    */
    function register(email, password, username) {
      return $http.post('/api/v1/users/', {
        username: username,
        password: password,
        email: email
      }).then(registerSuccessFn, registerErrorFn);

      /**
      * @name registerSuccessFn
      * @desc Log the new user in
      */
      function registerSuccessFn(data, status, headers, config) {
        Authentication.login(email, password);
      }

      /**
      * @name registerErrorFn
      * @desc Log "Epic failure!" to the console
      */
      function registerErrorFn(data, status, headers, config) {
        console.error('Epic failure!');
      }
    }
  }
})();