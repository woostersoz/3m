/**
* Sticky
* @namespace mmm.utils.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.utils.services')
    .factory('Sticky', Sticky);

  /**
  * @namespace Sticky
  */
  function Sticky() {
    /**
    * @name Sticky
    * @desc The factory to be returned
    */
    var Sticky = {
      createNote: createNote,
      //deleteNote: deleteNote,
      handleDeletedNote: handleDeletedNote
    };

    return Sticky;

    ////////////////////

    
    function createNote() {
    	var note = {
    			id: new Date().getTime(),
    	        title: 'New Sticky',
    	        body: ''
    	}
    	return note;
    }
    
    function handleDeletedNote(oldNotes, id) {
    	var newNotes = [];
    	
    	angular.forEach(oldNotes, function(note) {
    		if (note.id !== id) newNotes.push(note);
    	});
    	return newNotes;
    }
  }
})();