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
      downloadFile: downloadFile
      
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
  }
})();