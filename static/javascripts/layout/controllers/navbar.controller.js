/**
* NavbarController
* @namespace mmm.layout.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.layout.controllers')
    .controller('NavbarController', NavbarController);

  NavbarController.$inject = ['$scope', 'Authentication', 'Messages', '$timeout'];

  /**
  * @namespace NavbarController
  */
  function NavbarController($scope, Authentication, Messages, $timeout) {
    var vm = this;
    $scope.getUnreadNotifications = getUnreadNotifications;
    $scope.showNotificationsDropdown = false;
    
    vm.logout = logout;
    
    activate();
    
    function activate() {
    	var account = Authentication.getAuthenticatedAccount();
	    if (account) 
	    {
	    	Messages.getNotificationsCount().then(NotificationsCountSuccessFn, NotificationsCountErrorFn);
	    }
	    else {
	    	toastr.error('You need to login first');
	    	$location.path('/login'); 
	    }
    }
    
	    function NotificationsCountSuccessFn(data, status, headers, config) { 
	   	 if (data.data.count)  
	   	 {  
	   		$timeout(function() {
	   			$scope.notifications.count = data.data.count;
	   			$scope.notifications.unreadCount = data.data.unread_count;
	   		}, 0);
	   	 }
	       }
	    
	    function getUnreadNotifications() {
	    	Messages.getNotificationsUnread().then(NotificationsUnreadSuccessFn, NotificationsCountErrorFn);
	    }
	    
	    function getAllNotifications() {
	    	Messages.getNotificationsAll().then(NotificationsUnreadSuccessFn, NotificationsCountErrorFn);
	    }
	    
	    function NotificationsUnreadSuccessFn(data, status, headers, config) { 
		   	 if (data.data)  
		   	 {  
		   		$timeout(function() {
		   			$scope.notifications.unread = data.data;
		   			$scope.showNotificationsDropdown = true;
		   		}, 0);
		   	 }
		       }
	       
	       function NotificationsCountErrorFn(data, status, headers, config) {
	           // $location.url('/');
	           toastr.error('Messages could not be retrieved');
	         }
	       
    
    /**
    * @name logout
    * @desc Log the user out
    * @memberOf thinkster.layout.controllers.NavbarController
    */
    function logout() {
      Authentication.logout();
    }
  }
})();