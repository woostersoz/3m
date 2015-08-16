/**
* Profile
* @namespace mmm.profiles.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.profiles.services')
    .factory('Profile', Profile);

  Profile.$inject = ['$http'];

  /**
  * @namespace Profile
  */
  function Profile($http) {
    /**
    * @name Profile
    * @desc The factory to be returned
    * @memberOf mmm.profiles.services.Profile
    */
    var Profile = {
      destroy: destroy,
      get: get,
      update: update,
      getTimezones: getTimezones
    };

    return Profile;

    /////////////////////

    /**
    * @name destroy
    * @desc Destroys the given profile
    * @param {Object} profile The profile to be destroyed
    * @returns {Promise}
    * @memberOf mmm.profiles.services.Profile
    */
    function destroy(profile, company) {
      return $http.delete('/api/v1/company/' + company + '/users/' + profile.id + '/');
    }


    /**
    * @name get
    * @desc Gets the profile for user with username `username`
    * @param {string} username The username of the user to fetch
    * @returns {Promise}
    * @memberOf mmm.profiles.services.Profile
    */
    function get(userid, company) {
      return $http.get('/api/v1/company/' + company + '/users/' + userid + '/');
    }


    /**
    * @name update
    * @desc Update the given profile
    * @param {Object} profile The profile to be updated
    * @returns {Promise}
    * @memberOf mmm.profiles.services.Profile
    */
    function update(profile, company) {
      return $http.put('/api/v1/company/' + company + '/users/' + profile.id + '/', profile);
    }
    
    function getTimezones(company) {
        return $http.get('/api/v1/company/' + company + '/timezones/');
      }
    
    
  }
})();