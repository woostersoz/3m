/**
* Messages
* @namespace mmm.messages.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.messages.services')
    .factory('Messages', Messages);

  Messages.$inject = ['$http'];

  /**
  * @namespace Messages
  * @returns {Factory}
  */
  function Messages($http) {
    var Messages = {
      all: all,
      //create: create,
      get: get,
      getNotifications: getNotifications,
      getNotificationsCount: getNotificationsCount,
      getNotificationsUnread: getNotificationsUnread,
      getNotificationsAll: getNotificationsAll,
      setNotificationsRead: setNotificationsRead,
      getAll: getAll,
      getRooms: getRooms,
      getUserRooms: getUserRooms,
      getUserRoomsNotJoined: getUserRoomsNotJoined,
      joinRoom: joinRoom,
      createRoom: createRoom,
      submitMessage: submitMessage,
      getMessages: getMessages,
      getUserExports: getUserExports,
      downloadFile: downloadFile,
      getSlackMembership: getSlackMembership,
      getSlackMessages: getSlackMessages,
      formatSlackUserInfo: formatSlackUserInfo,
      formatSlackMsg: formatSlackMsg,
      submitSlackMessage: submitSlackMessage
      
    };

    return Messages;

    ////////////////////

    /**
    * @name all
    * @desc Get all Messages
    * @returns {Promise}
    * @memberOf mmm.Messages.services.Messages
    */
    function all(company) {
      return $http.get('/api/v1/company/' + company + '/messages/');
    }


    /**
     * @name get
     * @desc Get all Messages
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Messages.services.Messages
     */
    function getAll() {
      return $http.get('/api/v1/messages/');
    }
    
    function getNotifications() {
        return $http.get('/api/v1/collab/notifications/');
      }
    
    function getNotificationsCount(company) {
        return $http.get('/api/v1/company/' + company + '/collab/notifications/count/');
      }
    
    function getNotificationsUnread() {
        return $http.get('/api/v1/collab/notifications/unread/');
      }
    
    function getNotificationsAll(company) {
        return $http.get('/api/v1/company/' + company + '/collab/notifications/all/');
      }
    
    function setNotificationsRead(ids) {
        return $http.post('/api/v1/collab/notifications/setunread/', {'ids[]' : ids} );
    }
    
    
    /**
     * @name get
     * @desc Get the Messages of a given user
     * @param {string} username The username to get Messages for
     * @returns {Promise}
     * @memberOf mmm.Messages.services.Messages
     */
    function get(company, code) {
        return $http.get('/api/v1/company/' + company + '/messages/' + code + '/');
      //return $http.get('/api/v1/Messages/');
    }
    
    /* rooms start here */
    
    function getRooms(company) {
    	return $http.get('/api/v1/company/' + company + '/collab/rooms/');
    }
    
    function getUserRooms(company) {
    	return $http.get('/api/v1/company/' + company + '/collab/rooms/user/membership/');
    }
    
    function getUserRoomsNotJoined(company) {
    	return $http.get('/api/v1/company/' + company + '/collab/rooms/user/notjoined/');
    }
    
    
    function joinRoom(user, roomId, company) {
    	return $http.post('/api/v1/collab/room/user/join/', {'user_id' : user.id, 'nickname': user.username, 'room_id': roomId, 'company_id': company} );
    }
    
    function createRoom(user, room) {
    	return $http.post('/api/v1/collab/room/user/create/', {'user_id' : user.id, 'nickname': user.username, 'room_name': room.name, 'room_description': room.description, 'company_id': user.company} );
    }
    
    function submitMessage(user, message, roomId, snapshotId) {
    	if (snapshotId && snapshotId.length > 0)
    	   return $http.post('/api/v1/collab/room/user/message/create/', {'user_id' : user.id, 'nickname': user.username, 'room_id': roomId, 'message': message, 'company_id': user.company, 'snapshot_id': snapshotId} );
    	else
    		return $http.post('/api/v1/collab/room/user/message/create/', {'user_id' : user.id, 'nickname': user.username, 'room_id': roomId, 'message': message, 'company_id': user.company});
    }
    
    function getMessages(user, roomId) {
    	return $http.get('/api/v1/company/' + user.company + '/collab/room/messages/?roomId=' + roomId );
    }
    
    function getUserExports(user, page_number, per_page) {
    	return $http.get('/api/v1/exports/?page_number=' + page_number + '&per_page=' + per_page);
    }
    
    function downloadFile(user, file_id) {
    	return $http.get('/api/v1/download/' + file_id, {responseType: 'arraybuffer'} );
    }
    
    function getSlackMembership(company) {
    	return $http.get('/api/v1/company/' + company + '/collab/rooms/user/slack/');
    }
    
    function getSlackMessages(company, id, type) {
    	return $http.get('/api/v1/company/' + company + '/collab/rooms/user/slack/messages/?id=' + id + '&type=' + type);
    }
    
    function formatSlackUserInfo(message, users) {
    	if (message['user'] == 'USLACKBOT') //hardcoded for SlackBot
    	{
    		message['user_real_name'] = 'SlackBot';
    		message['user_name'] = 'slackbot';
    		message['user_image_url'] = '';
    		return message;
    	}
		for (var i=0; i < users.length; i++) {
			if (message['user'] && message['user'] == users[i]['id'])
			{
				message['user_real_name'] = users[i]['profile']['real_name'];
				message['user_name'] = users[i]['name'];
				message['user_image_url'] = users[i]['profile']['image_72'];
				break;
			}
		}
		return message;
	}
    
    function formatSlackMsg(text, edited, attachment) {
		var pattern = new RegExp("<(.*?)>", "g");
	    var match;
	    var editedText = "";
	    var attach_html = "";
	    var tempText = text;
	    
	    if (edited)
	       editedText = "<span class='muted-text'> (edited)</span>";
		
		if (attachment != null) {
			attach_html = "<div class='inline_attachment'>";
			attach_html += "<div class='attachment_pretext'>" + attachment['pretext'] + "</div>";
			attach_html += "<div class='inline_attachment_wrapper'>";
			attach_html += "<div class='attachment_bar' style='background:#" + attachment['color'] + ";'><div class='shim'></div></div>";
			attach_html += "<div class='content dynamic_content_max_width'>";
			if (attachment['author_link']) {
				attach_html += "<a href='" + attachment['author_link'] + "' target='_blank'><img class='attachment_author_icon' src='" + attachment['author_icon'] + "' width='16' height='16'></a>";
				attach_html += "<a href='" + attachment['author_link'] + "' target='_blank'><span class='attachment_author_name'>" + attachment['author_name'] + "</span></a>";
			}
			attach_html += "<div><span class='attachment_title'><a href='" + attachment['title_link']  + "' target='_blank'>" + attachment['title'] + "</a></span></div>";
			attach_html += "<div class='attachment_contents'>" + attachment['text'] + "</div>";
			attach_html += "</div></div></div>";
		}
		
    	while((match = pattern.exec(text)) != null) {
	    	//console.log(match);
    		var matchedStr = match[0];
    		var toBeReplacedStr = match[1];
    		var pipeIndex = toBeReplacedStr.indexOf('|');
    		if (pipeIndex != -1) // string contains a pipe
    		{
    			var linkUrl = toBeReplacedStr.substring(0, pipeIndex); // this is the link
    			var linkLabel = toBeReplacedStr.substring(pipeIndex+1); // this is the label
    		}
    		else // no pipe
    		{
    			var linkUrl = toBeReplacedStr;
    			var linkLabel = toBeReplacedStr;
    		}	
    		var hyperLink = "<a href='" + linkUrl + "' target='_blank'>" + linkLabel + "</a>";
    		tempText = tempText.replace(matchedStr, hyperLink);
	    		
    	}// end of while
    	if (match == null)
    		return tempText + editedText + attach_html;
    	return tempText + editedText + attach_html;
	}
    
    function submitSlackMessage(company, message, channelId, snapshotId) {
    	return $http.post('/api/v1/collab/room/user/slack/message/create/', {'company_id' : company, 'channel_id': channelId, 'message': message, 'snapshot_id': snapshotId} );
    }
    
    
  }
})();