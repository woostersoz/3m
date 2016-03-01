/**
* IndexController
* @namespace mmm.layout.controllers
*/
(function () {
  'use strict';

  angular
    .module('mmm.layout.controllers')
    .controller('IndexController', IndexController);

  IndexController.$inject = ['$scope', 'Authentication', '$location', '$timeout', '$state', 'Messages', '$modal', '$templateCache', '$rootScope', '$websocket', 'Integrations'];

  /**
  * @namespace IndexController
  */
  function IndexController($scope, Authentication, $location, $timeout, $state, Messages, $modal, $templateCache, $rootScope, $websocket, Integrations) {
	
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
    $scope.slackActive = false;
    $scope.slackSocket = '';
    $scope.authorize = authorize;
    $scope.downloadLeadsCsv = downloadLeadsCsv;
    // object for holding CSV download parameters
    $scope.csv = {}
    $scope.csv.param = []
     
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
    	 $location.path('/login'); 
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
	        Messages.getSlackMembership(account.company).then(SlackSuccessFn, SlackErrorFn);
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
    
    function SlackSuccessFn(data, status, headers, config) { 
    	 if (data.data.slck_auth_needed)
    		 $scope.slack_auth_needed = data.data.slck_auth_needed;
    	 
    	 if (data.data.slck_user_auth_needed)
    		 $scope.slack_user_auth_needed = data.data.slck_user_auth_needed;
    	 
	   	 if (data.data.slack_channels)
	   	 { 
	         $scope.slack_channels = data.data.slack_channels['channels'];	
	         $scope.slackActive = true;
	   	 }
	   	 if (data.data.slack_groups)
	   	 { 
	         $scope.slack_groups = data.data.slack_groups['groups'];		
	         $scope.slackActive = true;
	   	 }
	   	 if (data.data.users)
	   	 { 
	         $scope.slack_users = data.data.users;		 
	   	 }
	   	 if (data.data.slack_ims)
	   	 { 
	         $scope.slack_ims = data.data.slack_ims['ims'];		
	         for (var i=0; i < $scope.slack_ims.length; i++) { 
	        	 $scope.slack_ims[i] = Messages.formatSlackUserInfo($scope.slack_ims[i], $scope.slack_users);
	         }
	         $scope.slackActive = true;
	   	 }
	   	if (data.data.rtm && data.data.rtm.ok) // listen to the RTM API and add messages
		{
			$rootScope.slackSocket =  $websocket(data.data.rtm.url); // this is only to open up a socket for chart based simple messages
		}
   }
  
   function SlackErrorFn(data, status, headers, config) { 
      toastr.error("Could not retrieve Slack channels");
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
    
    
 // below functions copied from IntegrationsController
	  function authorize(companyInfo) {   
		    if (Authentication.getAuthenticatedAccount()) 
		    	Integrations.authorize(Authentication.getAuthenticatedAccount().company, companyInfo).then(AuthorizeSuccessFn, AuthorizeErrorFn);
		    else {
		    	toastr.error('You need to login first');
		    	$location.path('/login'); 
		    }
	    }
	    
	    function AuthorizeSuccessFn(data, status, headers, config) { 
	/*    	if (typeof eval('data.data.' + vm.source + '_access_token') != 'undefined')
	    	{
	    		vm.accessTokens[vm.source] = eval('data.data.' + vm.source + '_access_token');
	    		toastr.success(vm.accessTokens[vm.source]);
	    	}*/
	    	if (typeof data.data.auth_url != 'undefined')
	    	{   
	            window.location = data.data.auth_url;
	    	}
	    	else if (typeof data.data.error != 'undefined')
	    		toastr.error(data.data.error);
	    	else
	    	{
	    		toastr.success(data.data);
	    	}
	      }
	    
	    function AuthorizeErrorFn(data, status, headers, config) {
	        // $location.url('/');
	        toastr.error('Authorization could not be completed');
	      }
	    
	    /* Common CSV functions here */
	    
	    function downloadLeadsCsv() {
			if ($scope.csv.param[$scope.csv.param.length - 1] != 'csv') // add this parameter to indicate to the backend that this is a CSV
			   $scope.csv.param[$scope.csv.param.length] = 'csv';
			$scope.csv.functionToCall.apply(this, $scope.csv.param).then(CsvDownloadSuccessFxn, CsvDownloadErrorFxn);
		}
	
	    function CsvDownloadSuccessFxn(data, status, headers, config) {
	    	toastr.info('Export to CSV is scheduled. Check My Exports for details');
	    }
	    
	    function CsvDownloadErrorFxn(data, status, headers, config) {
	    	toastr.error('Export to CSV could not be scheduled');
	    }
	    
	    /* end of CSV functions */
    
    
    
  } // end of IndexController
  
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