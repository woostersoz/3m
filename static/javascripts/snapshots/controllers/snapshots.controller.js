/**
 * SnapshotsController
 * 
 * @namespace mmm.snapshots.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.snapshots.controllers', [ 'datatables' ]).controller(
			'SnapshotsController', SnapshotsController);

	SnapshotsController.$inject = [ '$scope', 'Snapshots', 'Authentication', 'Leads',
			'$location', 'DTOptionsBuilder', 'DTColumnDefBuilder',
			'DTColumnBuilder', 'DTInstances', '$filter', '$state',
			'$stateParams', '$document', '$window'];

	/**
	 * @namespace SnapshotsController
	 */
	function SnapshotsController($scope, Snapshots, Authentication, Leads, $state,
			$stateParams, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $document, $window, $interval) {
		
		var vm = this;
		
		// vm.isAuthenticated = Authentication.isAuthenticated();
		vm.snapshots = [];
		$scope.showSnapshot = showSnapshot;
		$scope.goBackToList = goBackToList;
		$scope.listMode = true;
		$scope.snapshotDate = '';
		$scope.chartName = '';
	
		activate();
		
		function goBackToList() {
			$scope.listMode = true;
		}
		
		function fillSnapshot(html) {
			angular.element(document.querySelector('#snapshot')).html(html);
			angular.element(document.querySelector('#snapshot')).find('input, textarea, button, select').attr('disabled', true);
			angular.element(document.querySelector('#snapshot')).find('button').hide();
		}
		
		function activate() {   
			var account = Authentication.getAuthenticatedAccount();
		    if (account) {
		    	Snapshots.getAll(account.company).then(GetSnapshotsSuccessFn, GetSnapshotsErrorFn);
		    }
	    }
	    
	    function GetSnapshotsSuccessFn(data, status, headers, config) {  
		    vm.snapshots = data.data;
		}
	    
        function GetSnapshotsErrorFn(data, status, headers, config) { 
		    
		}
        
        function showSnapshot(snapshot_id) {
        	var account = Authentication.getAuthenticatedAccount();
		    if (account) {
        	    Snapshots.get(account.company, snapshot_id).then(GetSnapshotSuccessFn, GetSnapshotErrorFn);
		    }
		}
        
        function GetSnapshotSuccessFn(data, status, headers, config) {  
		    if (data.data.snapshot_html) {
		    	fillSnapshot(data.data.snapshot_html);
		    	$scope.listMode = false;
		    	$scope.snapshotDate = data.data.updated_date;
		    	$scope.chartName = data.data.chart_name;
		    }
		}
	    
        function GetSnapshotErrorFn(data, status, headers, config) { 
		    
		}
	}
})();