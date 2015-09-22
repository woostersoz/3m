/**
* IndexController
* @namespace mmm.layout.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.layout.controllers')
    .controller('IndexController', IndexController);

  IndexController.$inject = ['$scope', 'Authentication', '$location', '$timeout', '$state', 'Messages', '$modal', '$templateCache', '$rootScope'];

  /**
  * @namespace IndexController
  */
  function IndexController($scope, Authentication, $location, $timeout, $state, Messages, $modal, $templateCache, $rootScope) {
	
	if (typeof window.callPhantom === 'function') {
		$timeout(function() { $rootScope.htmlReady(); }, 1000);
	}
	  
	var vm = this;

    vm.isAuthenticated = Authentication.isAuthenticated();
    $scope.rooms = [];
    $scope.subscribedRooms = [];
    $scope.roomJoined = '';
    $scope.roomCreated = '';
    $scope.notifications = {};
    $scope.notifications.count = 0;
    $scope.notifications.unreadCount = 0;
    $scope.notifications.unread = [];
    $scope.notifications.all = [];
    $scope.showChannelPreview = showChannelPreview;
    $scope.addChannel = addChannel;
    $scope.socket = '';
    $scope.socket2 = '';
    $scope.account = '';
     
    activate();
    if (Authentication.getAuthenticatedAccount()) 
       activateIO(Authentication.getAuthenticatedAccount()); // only activate if user is logged in
    
    /**
    * @name activate
    * @desc Actions to be performed when this controller is instantiated
    * @memberOf mmm.layout.controllers.IndexController
    */
    function activate() { 
      
      $scope.bodyClass = '';
      $scope.parentObj = {};
      $scope.parentObj.bodyClass = '';
      $scope.parentObj.preview = false;
      
      if (Authentication.getAuthenticatedAccount()) 
         $scope.account = Authentication.getAuthenticatedAccount();
      else {
    	  //$location.path('/login'); 
      }
      
    }
    
    function activateIO(account) {
    	
    	$scope.socket =  io.connect(
		        ":8000/notifications", // http://app.claritix.io/notifications
		        {
		            "reconnectionDelay": 5000,
		            "timeout": 10000,
		            "resource": "socket.io",
		           
		        }
		    );
    	
    	$scope.socket.on('connect', function(){
	        console.log('connect', $scope.socket);
	    });
    	$scope.socket.on('notification', function(notification){ 
	    	
	        console.log('notification', notification);
	        $timeout(function() {
	   			$scope.notifications.count++;
	   			$scope.notifications.unreadCount++; 
	   			//console.log(' you are n' + $state.current.url);
	   			if ($state.current.url == "/notifications")
	   				console.log('you are on n');;
	   		}, 0);
	        
	        if (notification.type === "leads_retrieved" || notification.type === "campaigns_retrieved" || notification.type === "activities_retrieved") {
	            if (notification.success) {
	               //toastr.success(notification.message, "Notification");
	            } else {
	                
	            }
	        } else if (notification.type === "error") {
	            toastr.error(notification.message)
	        } else {
	            //console.log(notification);
	        }
	    });
    	$scope.socket.on('disconnect', function(){
	        console.log('disconnect', $scope.socket);
	    });
	    
	    // code below from Calvinchengx on Github for Chat 
	   
	    $scope.socket2 = io.connect(":8000/chat", // http://app.claritix.io/notifications
        {
            "reconnectionDelay": 5000,
            "timeout": 10000,
            "resource": "socket.io",
           
        }
	    ); // // http://app.claritix.io/notifications - should be moved to services

	    $scope.socket2.on('connect', function () {
	    	console.log('connect-2', $scope.socket2);
	    	$scope.socket2.emit('nickname', $scope.account.username);
	        //$('#chat').addClass('connected');
	        //$scope.socket2.emit('join', 'test'); 
	    });

	    $scope.socket2.on('announcement', function (msg) {
	        //$('#lines').append($('<p>').append($('<em>').text(msg)));
	    	//toastr.info(msg);
	    });

	    $scope.socket2.on('nicknames', function (nicknames) {
	    	console.log("nicknames: " + nicknames);
	        $('#nicknames').empty().append($('<span>Online: </span>'));
	        for (var i in nicknames) {
	    		$('#nicknames').append($('<b>').text(nicknames[i]));
	        }
	    });

	    //$scope.socket2.on('msg_to_room', message);

	    $scope.socket2.on('reconnect', function () {
	        $('#lines').remove();
	        message('System', 'Reconnected to the server');
	    });

	    $scope.socket2.on('reconnecting', function () {
	        message('System', 'Attempting to re-connect to the server');
	    });

	    $scope.socket2.on('error', function (e) {
	        message('System', e ? e : 'A unknown error occurred');
	    });

	    function message (from, msg) {
	        $('#lines').append($('<p>').append($('<b>').text(from), msg));
	    }

	    // DOM manipulation
	    $(function () {
	        $('#set-nickname').submit(function (ev) {
	        	$scope.socket2.emit('nickname', $('#nick').val(), function (set) {
	                if (set) {
	                    clear();
	                    return $('#chat').addClass('nickname-set');
	                }
	                $('#nickname-err').css('visibility', 'visible');
	            });
	            return false;
	        });

	        $('#send-message').submit(function () {
	    		//message('me', "Fake it first: " + $('#message').val());
	        	$scope.socket2.emit('user message', $('#message').val());
	    		clear();
	    		$('#lines').get(0).scrollTop = 10000000;
	    		return false;
	        });

	        function clear () {
	            $('#message').val('').focus();
	        }
	    });
	    
	    if (account)  	
    	    //Messages.getRooms(account.company).then(RoomsSuccessFn, RoomsErrorFn);
	    	Messages.getUserRooms(account.company).then(RoomsSuccessFn, RoomsErrorFn);
	        Messages.getUserRoomsNotJoined(account.company).then(RoomsNotJoinedSuccessFn, RoomsNotJoinedErrorFn);
	    
    }
    
    function RoomsSuccessFn(data, status, headers, config) { 
	   	 if (data.data)
	   	 { 
	         $scope.subscribedRooms = data.data;		 
	   	 }
    }
   
    function RoomsErrorFn(data, status, headers, config) { 
       toastr.error("Could not retrieve channels");
    }
    
    function RoomsNotJoinedSuccessFn(data, status, headers, config) { 
	   	 if (data.data)
	   	 { 
	         $scope.rooms = data.data;		 
	   	 }
   }
  
   function RoomsNotJoinedErrorFn(data, status, headers, config) { 
      toastr.error("Could not retrieve channels");
   }
    
    function showChannelPreview(room) {
    	
    	var modalInstance = $modal.open({
    		templateUrl: staticUrl('templates/messages/room-preview.html'),
    		controller: modalController,
    		scope: $scope,
    		resolve: {
    			rooms: function() {
    				return $scope.rooms;
    			},
    			room: function() {
    				return room;
    			}
    		}
    		//className: 'ngdialog-theme-default',
    		//data: {channelId: channelId, name:name, description:description}
    		});
    	
    	modalInstance.result.then(function(room) {
    		$scope.roomJoined = room;
    		var account = Authentication.getAuthenticatedAccount();
    		if (account)
    		{ 
    	        Messages.joinRoom(account, room.id, account.company).then(JoinRoomSuccessFn, JoinRoomErrorFn);		
    		}
    	}, function() {
    		console.log('window closed');
    	}); 
    }
    
    function JoinRoomSuccessFn(data, status, headers, config) { 
        if (data.data["Error"])
        	toastr.error(data.data["Error"]);
        else 
        {
        	toastr.success(data.data["message"]);
        	if ($scope.account)  	
        	    //Messages.getRooms(account.company).then(RoomsSuccessFn, RoomsErrorFn);
    	    	Messages.getUserRooms($scope.account.company).then(RoomsSuccessFn, RoomsErrorFn);
    	        Messages.getUserRoomsNotJoined($scope.account.company).then(RoomsNotJoinedSuccessFn, RoomsNotJoinedErrorFn);
    	    
        	$scope.socket2.emit('join', data.data["roomId"]);
        } 
    }
    
    function JoinRoomErrorFn(data, status, headers, config) { 
    	toastr.error("Could not join channel");
    }
    
    function addChannel() {
  	  var modalInstance = $modal.open({
    		templateUrl: staticUrl('templates/messages/room-create.html'),
    		controller: modalCreateController,
    		scope: $scope,
    		resolve: {
    			newRoomForm: function() {
    				return $scope.newRoomForm;
    			}
    		}
    		//className: 'ngdialog-theme-default',
    		//data: {channelId: channelId, name:name, description:description}
    		});
    	
    	modalInstance.result.then(function(room) {  
    		$scope.roomCreated = room;
    		var account = Authentication.getAuthenticatedAccount();
    		if (account)
    		{ 
    	        Messages.createRoom(account, room).then(CreateRoomSuccessFn, CreateRoomErrorFn);		
    		}
    	}, function() {
    		console.log('window closed');
    	}); 
    }
    
    function CreateRoomSuccessFn(data, status, headers, config) { 
        if (data.data["Error"])
        	toastr.error(data.data["Error"]);
        else 
        {
        	toastr.success(data.data["message"]);
        	if ($scope.account)  	
        	    //Messages.getRooms(account.company).then(RoomsSuccessFn, RoomsErrorFn);
    	    	Messages.getUserRooms($scope.account.company).then(RoomsSuccessFn, RoomsErrorFn);
    	        Messages.getUserRoomsNotJoined($scope.account.company).then(RoomsNotJoinedSuccessFn, RoomsNotJoinedErrorFn);
        } 
    }
    
    function CreateRoomErrorFn(data, status, headers, config) { 
    	toastr.error("Could not create channel");
    }
    
    
  }
  
  var modalController = function ($scope, $modalInstance, rooms, room) {
	  
	  $scope.rooms = rooms;
	  $scope.room = room;
	  $scope.ok = function() {
		  $modalInstance.close($scope.room);
	  };
	  $scope.cancel = function() {
		  $modalInstance.dismiss('cancel');
	  };
  }
  
  

var modalCreateController = function ($scope, $modalInstance, newRoomForm) {
	  $scope.form = {};
	  $scope.submitForm = function(newRoom) {
		  if ($scope.form.newRoomForm.$valid) { 
			  $modalInstance.close(newRoom);
		  }
	  };
	 
	  $scope.cancel = function() {
		  $modalInstance.dismiss('cancel');
	  };
}


  
})();