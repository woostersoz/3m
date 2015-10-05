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
			'$stateParams', '$document', '$window', '$timeout', '$modal', 'Common', '$websocket', '$rootScope', '$anchorScroll'];

	/**
	 * @namespace MessagesController
	 */
	function MessagesController($scope, Messages, Authentication, $location,
			DTOptionsBuilder, DTColumnDefBuilder, DTColumnBuilder, DTInstances,
			$filter, $state, $stateParams, $document, $window, $timeout, $modal, Common, $websocket, $rootScope, $anchorScroll) {
		var vm = this;

		vm.isAuthenticated = Authentication.isAuthenticated();
		vm.messages = [];
		vm.rooms = [];
		vm.enteredRoom = '';
		$scope.setUnread = true;
		$scope.submitMessage = submitMessage;
		$scope.submitSlackMessage = submitSlackMessage;
		$scope.showSnapshotFromMessage = showSnapshotFromMessage;
		$scope.downloadFile = downloadFile;
		$scope.totalExports = 0;
	    $scope.exportsPerPage = 10;
	    $scope.currentPage = 1;

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
		  } 
		  else if ($state.current.name == "exports") {
			  if (account)
		         Messages.getUserExports(account, $scope.currentPage, $scope.exportsPerPage).then(getUserExportsSuccessFxn, getUserExportsErrorFxn);
		  }
		  else if ($state.current.name == "enterSlack") {
			  $scope.roomName = $stateParams.name;
			  $scope.roomDescription = $stateParams.purpose;
			  $scope.slackType = $stateParams.type;
			  $scope.slackId = $stateParams.id;
			  $rootScope.slackId = $stateParams.id;
			  if (account)
		         Messages.getSlackMessages(account.company, $scope.slackId, $scope.slackType).then(getSlackMessagesSuccessFxn, getSlackMessagesErrorFxn);
		  }
		  else {
			activate();
		}
		
		function getSlackMessagesSuccessFxn(data, status, headers, config) {
			var messageData = "";
			
			if (data.data.users) // save the Slack Users 
				$scope.slack_users = data.data.users;
	    	
			if (data.data.slack_messages.messages) // sort messages by time and format the text as well as user displays
			{
				$scope.slack_messages = data.data.slack_messages.messages;
			    $scope.slack_messages.sort(Common.sortByProperty("ts"));
			    
			    for (var i=0; i < $scope.slack_messages.length; i++) {
			    	var attachment = null;
			    	var edited = false;
			    	if ($scope.slack_messages[i].edited)
			    		edited = true;
			    	if ($scope.slack_messages[i].attachments)
			    		attachment = $scope.slack_messages[i].attachments[0];
			    	$scope.slack_messages[i].text = Messages.formatSlackMsg($scope.slack_messages[i].text, edited, attachment);
			    	$scope.slack_messages[i] = Messages.formatSlackUserInfo($scope.slack_messages[i], $scope.slack_users);
			    }
			    
			    if (data.data.rtm && data.data.rtm.ok) // listen to the RTM API and add messages
				{
		   		    var messageData = "";
		   		    
			    	$scope.slackUser = data.data.rtm.self.id;
					console.log('Slack URL is ' + data.data.rtm.url);
					$scope.slackSocket =  $websocket(data.data.rtm.url);
					$scope.slackId = $rootScope.slackId;
			    	
			    	$scope.slackSocket.onMessage(function(message){
			    		messageData = JSON.parse(message.data);
			    		var attachment = null;
			    		if (messageData['type'] == 'error')
			    			toastr.error(message.error.msg);
			    		else if (messageData['type'] == 'message')
				        {
				        	if (messageData['channel'] == $scope.slackId && messageData['subtype'] == 'message_changed') 
				        	{
				        		for (var i=0; i < $scope.slack_messages.length; i++) { // loop through to find the existing message that's been changed
				        			var old_message = $scope.slack_messages[i];
				        			if ($scope.slackId == messageData['channel'] && old_message['ts'] == messageData['message']['ts']) // change existing message
				        			{   
				        				if (messageData['attachments'])
				        					attachment = messageData['attachments'][0];
				        				$scope.slack_messages[i]['text'] = Messages.formatSlackMsg(messageData['text'], true, attachment);
				        				break;
				        			}	
				        		}
				        	}
				        	else if ((messageData['channel'] == $scope.slackId && !messageData['subtype']) || (messageData['channel'] == $scope.slackId && messageData['subtype'] == 'file_share')) // if it is a message for the group/channel currently being viewed, add it to the scope array and display on screen
				            {
				            	if (!messageData['reply_to']) //skip reply_to to avoid duplicates - may need to be changed
				            	{
					            	var newMessage = {};
					            	newMessage['user'] = messageData['user'];
					            	newMessage['ts'] = messageData['ts'];
					            	if (messageData['attachments'])
			        					attachment = messageData['attachments'][0];
					            	newMessage['text'] = Messages.formatSlackMsg(messageData['text'], false, attachment);
					            	newMessage = Messages.formatSlackUserInfo(newMessage, $scope.slack_users);
					            	$scope.slack_messages.push(newMessage);
				            	}
				            }
				            console.log(messageData);
				        }
				    });
				}
			    
			    scrollToBottom();
			}
			else
				toastr.error("Unable to get Slack messages");
		}
		
        function getSlackMessagesErrorFxn(data, status, headers, config) {
        	toastr.error("Unable to get Slack messages");
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
				//for (var i=0; i < vm.messages.length; i++)
				//	vm.messages[i].user.image_url = staticUrl(vm.messages[i].user.image_url);
				//$scope.roomName = vm.messages[0].room.name;
				//$scope.roomDescription = vm.messages[0].room.description;
				scrollToBottom();
			}
		}

		function getMessagesErrorFn(data, status, headers, config) {
			toastr.error("Could not retrieve messages");
		}
		
		function getUserExportsSuccessFxn(data, status, headers, config) {
			if (data.data.results) {
				vm.exports = data.data.results;
				$scope.thisSetCount = data.data.results.length;
				$scope.totalExports = data.data.count;
				$scope.startExportCounter = ($scope.currentPage - 1) * $scope.exportsPerPage + 1;
			    $scope.endExportCounter = ($scope.thisSetCount < $scope.exportsPerPage) ? $scope.startExportCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.exportsPerPage;
				
				
			}
		}
		
		function getUserExportsErrorFxn(data, status, headers, config) {
			toastr.error("Could not retrieve exports");
		}
		
		function downloadFile(file_id, file_name) {
			$scope.downloadFileName = file_name;
			if (account) {
				Messages.downloadFile(account, file_id).then(downloadFileSuccess, downloadFileError);
			}
		}
		
		function downloadFileSuccess(data, status, headers, config) {
			var headers = data.headers();
			var content_type = 'application/pdf';
			if (headers['content-type'])
			   content_type = headers['content-type'];
			var anchor = angular.element('<a/>');
			anchor.css({display: 'none'});
			angular.element(document.body).append(anchor);
			
			/*anchor.attr({
				href: 'data:attachment/csv,' + encodeURIComponent(data.data),
				target: '_blank',
				download: $scope.downloadFileName
			})[0].click();*/
			var csvData = new Blob([data.data], { type: content_type });
			var csvUrl = URL.createObjectURL(csvData);
			
			anchor.attr({
				href: csvUrl,
				download: $scope.downloadFileName
			})[0].click();
			
			anchor.remove();
		}
		
        function downloadFileError(data, status, headers, config) {
			
		}
		
		$scope.pageChanged = function(newPage) {
			$scope.currentPage = newPage;
			if (account)
		         Messages.getUserExports(account, $scope.currentPage, $scope.exportsPerPage).then(getUserExportsSuccessFxn, getUserExportsErrorFxn);
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
		
		function submitSlackMessage(room) {
			var account = Authentication.getAuthenticatedAccount();
			if (account) {
				var newMessage = {}
				newMessage.text = room.message;
				newMessage.channel = $scope.slackId;
				newMessage.type = 'message';
				newMessage.id = moment().unix();
				$scope.slackSocket.send(newMessage);
				newMessage.ts = newMessage.id;
				newMessage.user = $scope.slackUser;
				newMessage.text = Messages.formatSlackMsg(newMessage.text, false, null);
            	newMessage = Messages.formatSlackUserInfo(newMessage, $scope.slack_users);
            	$scope.slack_messages.push(newMessage);
            	scrollToBottom();
				angular.element(document.querySelector('#room__message')).val(
						'');
				console.log(newMessage);
			}
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
			$location.hash('bottom');
			$anchorScroll();
			/*$timeout(
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
					}, 1000);*/
		}

		function inArray(array, id) {
			for (var i = 0; i < array.length; i++) {
				return (array[i][0].id === id)
			}
			return false;
		}
		
		
		
		
	}
})();