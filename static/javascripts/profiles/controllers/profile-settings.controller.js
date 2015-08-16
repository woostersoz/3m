/**
* ProfileSettingsController
* @namespace mmm.profiles.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.profiles.controllers')
    .controller('ProfileSettingsController', ProfileSettingsController);

  ProfileSettingsController.$inject = [
    '$location', '$stateParams', 'Authentication', 'Profile', '$window', '$timeout'
  ];

  /**
  * @namespace ProfileSettingsController
  */
  function ProfileSettingsController($location, $stateParams, Authentication, Profile, $window, $timeout) {
    var vm = this;

    vm.destroy = destroy;
    vm.update = update;
    //$scope.timezone = $parent.scope.timezone;

    activate();


    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated.
    * @memberOf mmm.profiles.controllers.ProfileSettingsController
    */
    function activate() {
      var authenticatedAccount = Authentication.getAuthenticatedAccount();
      var id = $stateParams.id;//.substr(1);

      // Redirect if not logged in
      if (!authenticatedAccount) {
        $location.url('/');
        toastr.error('You are not authorized to view this page.');
      } else {
        // Redirect if logged in, but not the owner of this profile.
        /*if (authenticatedAccount.id !== parseInt(id)) {
          $location.url('/');
          toastr.error('You are not authorized to view this page.');
        } */
      }

      Profile.get(id, authenticatedAccount.company).then(profileSuccessFn, profileErrorFn);
      Profile.getTimezones(authenticatedAccount.company).then(tzSuccessFn, tzErrorFn);

      /**
      * @name profileSuccessFn
      * @desc Update `profile` for view
      */
      function profileSuccessFn(data, status, headers, config) {
        vm.profile = data.data;
      }
      
      function tzSuccessFn(data, status, headers, config) {
    	  if (data.data.timezones)
             vm.timezones = data.data.timezones;
    	  else
    		 toastr.error('Could not get time zones'); 
        }

      /**
      * @name profileErrorFn
      * @desc Redirect to index
      */
      function profileErrorFn(data, status, headers, config) {
        //$location.url('/');
        toastr.error('That user does not exist.');
      }
      
      function tzErrorFn(data, status, headers, config) {
          toastr.error('Could not get time zones');
        }
    }


    /**
    * @name destroy
    * @desc Destroy this user's profile
    * @memberOf mmm.profiles.controllers.ProfileSettingsController
    */
    function destroy() {
      var authenticatedAccount = Authentication.getAuthenticatedAccount();
      if (!authenticatedAccount) {
          $location.url('/');
          toastr.error('You are not authorized to view this page.');
        }
      Profile.destroy(vm.profile.username, authenticatedAccount.company).then(profileSuccessFn, profileErrorFn);

      /**
      * @name profileSuccessFn
      * @desc Redirect to index and display success snackbar
      */
      function profileSuccessFn(data, status, headers, config) {
        Authentication.unauthenticate();
        window.location = '/';

        toastr.info('Your account has been deleted.');
      }


      /**
      * @name profileErrorFn
      * @desc Display error snackbar
      */
      function profileErrorFn(data, status, headers, config) {
        toastr.error(data.error);
      }
    }


    /**
    * @name update
    * @desc Update this user's profile
    * @memberOf mmm.profiles.controllers.ProfileSettingsController
    */
    function update() { 
    	var authenticatedAccount = Authentication.getAuthenticatedAccount();
        if (!authenticatedAccount) {
            $location.url('/');
            toastr.error('You are not authorized to view this page.');
          }
      Profile.update(vm.profile, authenticatedAccount.company).then(profileSuccessFn, profileErrorFn);

      /**
      * @name profileSuccessFn
      * @desc Show success snackbar
      */
      function profileSuccessFn(data, status, headers, config) {
        toastr.success('Your profile has been updated.');
        $timeout(function() {
        	window.location = '/';
        }, 1000);
      }


      /**
      * @name profileErrorFn
      * @desc Show error snackbar
      */
      function profileErrorFn(data, status, headers, config) {
        toastr.error(data.error);
      }
    }
  }
})();