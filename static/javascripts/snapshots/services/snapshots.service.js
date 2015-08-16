/**
* Snapshots
* @namespace mmm.snapshots.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.snapshots.services')
    .factory('Snapshots', Snapshots);

  Snapshots.$inject = ['$http'];

  /**
  * @namespace Snapshots
  * @returns {Factory}
  */
  function Snapshots($http) {
    var Snapshots = {
      all: all,
      //create: create,
      get: get,
      getAll: getAll,
      saveSnapshot: saveSnapshot,
      
    };

    return Snapshots;

    ////////////////////

    /**
    * @name all
    * @desc Get all Snapshots
    * @returns {Promise}
    * @memberOf mmm.Snapshots.services.Snapshots
    */
    function all(userid) {
      return $http.get('/api/v1/Account/' + userid + '/snapshots/');
    }

    /**
     * @name get
     * @desc Get all Snapshots
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Snapshots.services.Snapshots
     */
    function getAll(company) {
      return $http.get('/api/v1/company/' + company + '/analytics/snapshots/');
    }
    

    function get(company, snapshotId) {
      return $http.get('/api/v1/company/' + company + '/analytics/snapshot/' + snapshotId );
      //return $http.get('/api/v1/Snapshots/');
    }
   
    function saveSnapshot(company, snapshotHtml, chartName) {
    	return $http.post('/api/v1/company/' + company + '/analytics/snapshot/save/', {
    		snapshotHtml : snapshotHtml,
    		chartName : chartName
    	});
    }
    
    
  }
})();