/**
* Binders
* @namespace mmm.binders.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.binders.services')
    .factory('Binders', Binders);

  Binders.$inject = ['$http'];

  /**
  * @namespace Binders
  * @returns {Factory}
  */
  function Binders($http) {
    var Binders = {
      all: all,
      //create: create,
      get: get,
      getAll: getAll,
      getAllBinderTemplates: getAllBinderTemplates,
      saveBinderTemplate: saveBinderTemplate,
      getBinders: getBinders
      
    };

    return Binders;

    ////////////////////

    /**
    * @name all
    * @desc Get all Binders
    * @returns {Promise}
    * @memberOf mmm.Binders.services.Binders
    */
    function all(userid) {
      return $http.get('/api/v1/Account/' + userid + '/binders/');
    }

    /**
     * @name get
     * @desc Get all Binders
     * @param {none}
     * @returns {Promise}
     * @memberOf mmm.Binders.services.Binders
     */
    function getAll(company) {
      return $http.get('/api/v1/company/' + company + '/analytics/binders/');
    }
    
    function getAllBinderTemplates(company) {
        return $http.get('/api/v1/company/' + company + '/analytics/binder-templates/');
      }
    

    function get(company, binderId) {
      return $http.get('/api/v1/company/' + company + '/analytics/binder/' + binderId );
      //return $http.get('/api/v1/Binders/');
    }
   
    function saveBinderTemplate(company, binderTemplate) {
    	return $http.post('/api/v1/company/' + company + '/analytics/binder-template/', {
    		binderTemplate : binderTemplate
    	});
    }
    
    function getBinders(company, binderTemplateId) {
    	return $http.get('/api/v1/company/' + company + '/analytics/binders/' + binderTemplateId + '/' );
    }
    
    
  }
})();