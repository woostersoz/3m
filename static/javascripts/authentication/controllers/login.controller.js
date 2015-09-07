/**
* LoginController
* @namespace mmm.authentication.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.authentication.controllers')
    .controller('LoginController', LoginController);

  LoginController.$inject = ['$location', '$scope', 'Authentication'];

  /**
  * @namespace LoginController
  */
  function LoginController($location, $scope, Authentication) {
    var vm = this;

    vm.login = login;
    $scope.logoUrl = staticUrl('images/logo.png');

    activate();

    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf thinkster.authentication.controllers.LoginController
    */
    function activate() {
    	
      $scope.images = [];	

      // If the user is authenticated, they should not be here.
      if (Authentication.isAuthenticated()) { toastr.info('loggedin');
        $location.url('/');
      }
      else
      { //toastr.info('not loggedin');
    	$scope.parentObj.bodyClass = 'login'; //  refers to object in IndexController
    	Authentication.getLoginTemplate().then(LoginSuccessFxn, LoginErrorFxn);
      }
    }
    
    function LoginSuccessFxn(data, status, headers, config)
    {
    	var loadScript = function() {
    		var script = document.createElement('script');
    		script.type = 'text/javascript';
    		script.src = '/static/theme/assets/admin/pages/scripts/login-soft.js';
    		document.body.appendChild(script);
    		/*    	  script = document.createElement('script');
    	  script.type = 'text/javascript';
    	  script.src = '/static/theme/assets/global/plugins/backstretch/jquery.backstretch.min.js';
    	  document.body.appendChild(script);
     	  angular.element.backstretch([
               "/static/theme/assets/admin/pages/media/bg/1.jpg",
               "/static/theme/assets/admin/pages/media/bg/2.jpg",
               "/static/theme/assets/admin/pages/media/bg/3.jpg",
               "/static/theme/assets/admin/pages/media/bg/4.jpg",
    	                 ], { fade: 1000, duration: 8000});*/
    	}

    	$scope.$on('$viewContentLoaded', function() {
    		loadScript();
    	})

    	$scope.images = ["/static/theme/assets/admin/pages/media/bg/1.jpg",
    	                 "/static/theme/assets/admin/pages/media/bg/2.jpg",
    	                 "/static/theme/assets/admin/pages/media/bg/3.jpg",
    	                 "/static/theme/assets/admin/pages/media/bg/4.jpg",];
    } // end of success fxn

    function LoginErrorFxn(data, status, headers, config) {
    	toastr.error(data.errors);
    }

    /**
    * @name login
    * @desc Log the user in
    * @memberOf mmm.authentication.controllers.LoginController
    */
    function login() {
      Authentication.login(vm.email, vm.password);
    }
  }
})();