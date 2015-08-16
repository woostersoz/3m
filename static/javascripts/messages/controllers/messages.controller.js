/**
 * MessagesController
 * @namespace mmm.messages.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.messages.controllers', [ 'datatables' ]).controller(
			'MessagesController', MessagesController);

	MessagesController.$inject = [ '$scope', 'Messages', 'Authentication',
			'$location', 'DTOptionsBuilder', 'DTColumnDefBuilder',
			'DTColumnBuilder', 'DTInstances', '$filter', '$state',
			'$stateParams', '$document', '$window', '$timeout', '$modal'];

	/**
	 * @namespace MessagesController
	 */
	function MessagesController($scope, Messages, Authentication, $location,
			DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances,
			$filter, $state, $stateParams, $document, $window, $timeout, $modal) {
		var vm = this;

		vm.isAuthenticated = Authentication.isAuthenticated();
		vm.messages = [];
		vm.rooms = [];
		vm.enteredRoom = '';
		$scope.setUnread = true;
		$scope.submitMessage = submitMessage;
		$scope.showSnapshotFromMessage = showSnapshotFromMessage;

		//    $scope.$state = $state;
		//    $scope.scopeName = $state.current.name
		var account = Authentication.getAuthenticatedAccount();

		if ($state.current.name == "notifications") {
			if (account)
				getAllNotifications(account.company);
		} else if ($state.current.name == "enterChannel") {
			if (!(typeof $stateParams == 'undefined')) {
				if ($stateParams.enteredRoom) {
					vm.enteredRoom = $stateParams.enteredRoom;
					$scope.roomName = $stateParams.roomName;
					$scope.roomDescription = $stateParams.roomDescription;
					$scope.$parent.socket2.emit('join', vm.enteredRoom);
					Messages.getMessages(account, vm.enteredRoom).then(
							getMessagesSuccessFn, getMessagesErrorFn);
					$scope.$parent.socket2.on('msg_to_room', publishMessage);
					$scope.$parent.socket2.on('user_typing', publishTyping);
				}
			}
			//if (account)  	
			//Messages.getRooms(account.company).then(RoomsSuccessFn, RoomsErrorFn);;
		} else {
			activate();
		}

		function publishTyping(from, msg) { 
			if (vm.enteredRoom
					&& (vm.enteredRoom == msg.room.id)
					    && msg.nickname != account.username) {
				angular.element(document.querySelector('#user-typing')).html(msg.message);
			}
		}
		
		function publishMessage(from, msg) {  //alert(msg.room.id + ' &&&&&' + vm.enteredRoom.room.id);
			if (vm.enteredRoom 
					&& (vm.enteredRoom == msg.room.id)) {
				vm.messages.push(msg);
				$scope.$digest();
				scrollToBottom();
			}
		}

		function getMessagesSuccessFn(data, status, headers, config) {
			if (data.data) {
				vm.messages = data.data;
				//$scope.roomName = vm.messages[0].room.name;
				//$scope.roomDescription = vm.messages[0].room.description;
				scrollToBottom();
			}
		}

		function getMessagesErrorFn(data, status, headers, config) {
			toastr.error("Could not retrieve messages");
		}

		function RoomsSuccessFn(data, status, headers, config) {
			if (data.data) {
				vm.rooms = data.data;
			}
		}

		function RoomsErrorFn(data, status, headers, config) {
			toastr.error("Could not retrieve channels");
		}
		/*    $scope.$state = $state;
		 $scope.scopeName = $state.current.name*/

		/**
		 * @name activate
		 * @desc Actions to be performed when this controller is instantiated
		 * @memberOf mmm.symbols.controllers.MessagesController
		 */
		function activate() {
			var account = Authentication.getAuthenticatedAccount();
			if (account)
				Messages.getNotificationsCount(account.company).then(
						MessagesSuccessFn, MessagesErrorFn);
			else {
				toastr.error('You need to login first');
				$location.path('/login');
			}
		}

		function getAllNotifications(company) {
			Messages.getNotificationsAll(company).then(
					NotificationsAllSuccessFn, NotificationsAllErrorFn);
		}

		function NotificationsAllSuccessFn(data, status, headers, config) {
			if (data.data) {
				$timeout(function() {
					$scope.notifications.all = data.data;
				}, 0);

				if ($scope.setUnread)
					$timeout(
							function() {
								var ids = [];
								for (var i = 0; i < $scope.notifications.all.length; i++) {
									$scope.notifications.all[i].read = true;
									ids.push($scope.notifications.all[i].id);
								}
								$scope.notifications.unreadCount = 0;
								$scope.setUnread = false;
								Messages.setNotificationsRead(ids).then(
										NotificationsSetUnreadSuccessFn,
										NotificationsSetUnreadErrorFn);
							}, 3000);
			}
		}

		function NotificationsSetUnreadSuccessFn(data, status, headers, config) {

		}

		function NotificationsSetUnreadErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Messages could not be set as read');
		}

		function NotificationsAllErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Messages could not be retrieved');
		}

		function MessagesSuccessFn(data, status, headers, config) {
			if (data.data.length > 0) // do something
			{

			}
		}

		function MessagesErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Messages could not be retrieved');
		}

		function submitMessage(room) {
			var account = Authentication.getAuthenticatedAccount();
			if (account) {
				var newMessage = {}
				newMessage.message = room.message;
				newMessage.user_id = account.id;
				newMessage.nickname = account.username;
				newMessage.company_id = account.company;
				newMessage.updated_date = new Date();
				//TO-DO - add image
				//vm.messages.push(newMessage);
				Messages.submitMessage(account, room.message, vm.enteredRoom)
						.then(submitMessageSuccessFn, submitMessageErrorFn);
			}
		}

		function submitMessageSuccessFn(data, status, headers, config) {
			if (data.data) {
				$scope.$parent.socket2.emit('user message', data.data.message,
						vm.enteredRoom);
				scrollToBottom();
				angular.element(document.querySelector('#room__message')).val(
						'');
			}
		}

		function submitMessageErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Message could not be sent');
		}
		
		function showSnapshotFromMessage(snapshotHtml) {
			var modalInstance = $modal.open({
	    		templateUrl: staticUrl('templates/analytics/snapshot-modal.html'),
	    		controller: modalController,
	    		scope: $scope,
	    		resolve: {
	    			snapshotHtml: function() {
	    				return snapshotHtml;
	    			},
	    		},
	    		//dialogClass: 'modal-large',
	    		size: 'large'
	    		});
	    	
	    	modalInstance.result.then(function() { 
	    		
	    		
	    	}, function() {
	    		
	    	}); 
		}
	
	var modalController = function ($scope, $modalInstance, snapshotHtml) {
		  
		  $scope.snapshotHtml = snapshotHtml;
		
		  function fillSnapshot(html) {
				angular.element(document.querySelector('#snapshot')).html(html);
				angular.element(document.querySelector('#snapshot')).find('input, textarea, button, select').attr('disabled', true);
				angular.element(document.querySelector('#snapshot')).find('button').hide();
			}
		  
		  //$modalInstance.opened.then(fillSnapshot(snapshotHtml));
		  
		  $scope.ok = function() {
			  $modalInstance.close();
		  };
		  $scope.cancel = function() {
			  $modalInstance.dismiss('cancel');
		  };
	  }
	  
	//emit 'user is typing' event
	angular.element(document.querySelector('#room__message')).keypress(function() {
		var message = {};
		message.room = {};
		message.room.id = vm.enteredRoom;
		message.nickname = account.username;
		message.message = message.nickname + " is typing"; 
		$scope.$parent.socket2.emit('user typing', message,
				vm.enteredRoom);
	});
	
    var delay = (function() {
    	var timer = 0;
    	return function(callback, ms){
    		clearTimeout(timer);
    		timer = setTimeout(callback, ms);
    	};
    })();
    
    angular.element(document.querySelector('#room__message')).keyup(function() {
    	delay(function() {
    		var message = {};
    		message.room = {};
    		message.room.id = vm.enteredRoom;
    		message.nickname = account.username;
    		message.message = "";
    		$scope.$parent.socket2.emit('user typing', message,
    				vm.enteredRoom);
    	}, 1000);
    });
	
		function scrollToBottom() {
			$timeout(
					function() {
						var timeline_div = angular.element(document
								.querySelector('.timeline'));
						//timeline_div.scrollTop(timeline_div.prop("scrollHeight"));
						angular
								.element(document.querySelector('.timeline'))
								.animate(
										{
											scrollTop : angular
													.element(document
															.querySelector('.timeline'))[0].scrollHeight
										}, 1000);
					}, 1000);
		}

		function inArray(array, id) {
			for (var i = 0; i < array.length; i++) {
				return (array[i][0].id === id)
			}
			return false;
		}
	}
})();