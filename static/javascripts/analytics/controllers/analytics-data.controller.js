/**
 * AnalyticsDataController
 * 
 * @namespace mmm.analytics.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.analytics.controllers').controller(
			'AnalyticsDataController', AnalyticsDataController);

	AnalyticsDataController.$inject = [ '$scope', 'Analytics', 'Authentication',
	                                'Leads', 'Snapshots', '$location', '$filter',
	                                '$state', '$stateParams', '$document', '$window', 'Sticky',
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope'];

	/**
	 * @namespace AnalyticsDataController
	 */
	function AnalyticsDataController($scope, Analytics, Authentication, Leads,
			Snapshots, $location, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope, $interval) {

		var vm = this;
		vm.charts = [];
		$scope.dataSelection = "";
		$scope.calculateAnalytics = calculateAnalytics;
		
		var account = Authentication.getAuthenticatedAccount();
		if (account) {
		    Analytics.getChartsByCompany(account.company)
				.then(ChartsSuccessFn, ChartsErrorFn);
		}
		else {
			toastr.error("You need to login first");
		}
		
		function ChartsSuccessFn(data, status, headers, config) {
			if (data.data.results) // they could contain  Mkto, SFDC or HSPT leads
			{ 
				vm.charts = data.data.results[0];
			}
		}
		
		function ChartsErrorFn(data, status, headers, config) {
			toastr.error("Could not find charts for company");
			return false;
		} 
		
		function calculateAnalytics(chart_name, system_type, chart_title, mode) {
			Analytics.calculateAnalytics(account.company, chart_name, system_type, chart_title, mode).then(CalculateSuccessFn, CalculateErrorFn);
		}
		
		function CalculateSuccessFn(data, status, headers, config) {
			toastr.info("Extraction of analytics triggered in background");
		} 
		
		function CalculateErrorFn(data, status, headers, config) {
			toastr.error("Could not trigger extraction of analytics");
			return false;
		} 

	}
})();