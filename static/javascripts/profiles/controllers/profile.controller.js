/**
* ProfileController
* @namespace mmm.profiles.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.profiles.controllers')
    .controller('ProfileController', ProfileController);

  ProfileController.$inject = ['$location', '$state', '$stateParams', 'Profile', 'Authentication'];

  /**
  * @namespace ProfileController
  */
  function ProfileController($location, $state, $stateParams, Profile, Authentication) {
    var vm = this;

    vm.profile = undefined;


    activate();

    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.profiles.controllers.ProfileController
    */
    function activate() {
      var userid = $stateParams.id; // alert(username); //substr(1);
      var account = Authentication
		.getAuthenticatedAccount();
      if (account)
           Profile.get(userid, account.company).then(profileSuccessFn, profileErrorFn);

      /**
      * @name profileSuccessProfile
      * @desc Update `profile` on viewmodel
      */
      function profileSuccessFn(data, status, headers, config) {
        vm.profile = data.data;
      }


      /**
      * @name profileErrorFn
      * @desc Redirect to index and show error Snackbar
      */
      function profileErrorFn(data, status, headers, config) {
        $location.url('/');
        toastr.error('That user does not exist.');
      }

    }
  }
})();