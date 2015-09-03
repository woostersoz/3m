/**
 * AnalyticsController
 * 
 * @namespace mmm.analytics.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.analytics.controllers', [ 'datatables' ]).controller(
			'AnalyticsController', AnalyticsController);

	AnalyticsController.$inject = [ '$scope', 'Analytics', 'Authentication',
	                                'Leads', 'Snapshots', '$location', 'DTOptionsBuilder',
	                                'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter',
	                                '$state', '$stateParams', '$document', '$window', 'Sticky',
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope', 'AnalyticsCharts', 'Social', 'Websites', '$q'];

	/**
	 * @namespace AnalyticsController
	 */
	function AnalyticsController($scope, Analytics, Authentication, Leads,
			Snapshots, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope, AnalyticsCharts, Social, Websites, $q, $interval) {

		var vm = this;
		vm.analytics = [];
		vm.leads = [];
		$scope.leads = [];
	    $scope.totalLeads = 0;
	    $scope.leadsPerPage = 10;
	    $scope.currentPage = 1;
	
		$scope.notes = [];
		$scope.createNote = createNote;
		$scope.deleteNote = deleteNote;
		//$scope.handleDeletedNote = Sticky.handleDeletedNote;
		$scope.showLeads = false;
		$scope.showLeadsDuration = false;
		$scope.showTweets = false;
		$scope.showWebsiteVisitors = false;
		$scope.showCarousel = true;
		$scope.showChart = false;
		$scope.notFirstChart = false; // this is set to false only when page is loaded else always true
		
		$scope.data = [];
		$scope.strict = false;
		$scope.chartName = '';
		$scope.chartType = '';
		$scope.startDate = '';
		$scope.endDate = '';
		$scope.snapshot = snapshot;
		$scope.staticUrl = staticUrl;
		$scope.drawChart = drawChart;
		$scope.postToChannel = postToChannel;
		$scope.barUrl = staticUrl('images/analytics-bar.png');
		$scope.lineUrl = staticUrl('images/analytics-line.png');
		$scope.rowUrl = staticUrl('images/analytics-row.png');
		$scope.pieUrl = staticUrl('images/analytics-pie.png');
		
		$scope.filters = {};
		$scope.filterValues = {};
		$scope.selectedFilterValues = {};
		
		var account = Authentication.getAuthenticatedAccount();
		if (account) {
		    Analytics.getChartsByCompany(account.company)
				.then(ChartsSuccessFn, ChartsErrorFn);
		}
		else {
			toastr.error("You need to login first");
		}
		
		function ChartsSuccessFn(data, status, headers, config) {
			if (data.data.results.length > 0) // they could contain  Mkto, SFDC or HSPT leads
			{ 
				$scope.charts = data.data.results;
				for (var i=0; i < $scope.charts.length; i++)
					$scope.charts[i].src = staticUrl($scope.charts[i].src);
			}
			else {
				toastr.error("Could not find charts for company");
			}
		}
		
		function ChartsErrorFn(data, status, headers, config) {
			toastr.error("Could not find charts for company");
			return false;
		} 
		
		/*$scope.images = [ {
			"src" : $scope.barUrl,
			"url" : "timeline",
			"title" : "Timeline",
			"name" : "sources_bar",
			"system_type" : "MA"
		}, {
			"src" : $scope.lineUrl,
			"url" : "pipeline_duration",
			"title" : "Pipeline Duration",
			"name" : "pipeline_duration",
			"system_type" : "MA"
		}, {
			"src" : $scope.rowUrl,
			"url" : "contacts_distr",
			"title" : "Contacts Distribution",
			"name" : "contacts_distr",
			"system_type" : "MA"
		}, {
			"src" : $scope.pieUrl,
			"url" : "source_pie",
			"title" : "Source Breakdown",
			"name" : "source_pie",
			"system_type" : "MA"
		},
		{
			"src" : $scope.pieUrl,
			"url" : "revenue_source_pie",
			"title" : "Revenue by Source",
			"name" : "revenue_source_pie",
			"system_type" : "MA"
		},

		];*/
		
		// initialize for table row detail display
		DTInstances.getLast().then(function (dtInstance) {
	        vm.dtInstance = dtInstance;
	    });
	    
	    
		$scope.showingContact = [];
	    for (var i=0, length = vm.leads.length; i < length; i++) {
	    	$scope.showingContact[vm.leads[i].id] = false;
	    }
	    
	    $scope.showContactDetails = function(lead) {
	    	$scope.showingContact[lead.id] = true;
	    }
	    
	    $scope.hideContactDetails = function(lead) {
	    	$scope.showingContact[lead.id] = false;
	    }
	    
	    $scope.showTheCarousel = function() { 
	    	$scope.showCarousel = true;
	    }
	    
	    // object for holding CSV download parameters
	    $scope.csv = {}
	    $scope.csv.param = []
	    $scope.downloadLeadsCsv = downloadLeadsCsv;

		// below for collaboration in chart
		$scope.channelInModal = true;
		$scope.subscribedRooms = '';
		$scope.latestSnapshotId = '';
		$scope.lastRoomId = '';

		function createNote() {
			$scope.notes.push(Sticky.createNote());
		}

		function deleteNote(id) {
			$scope.notes = Sticky.handleDeletedNote($scope.notes, id);
		}
		
		$scope.startSpin = function() {
			 if (!$scope.spinneractive) {
			        usSpinnerService.spin('spinner-1');
			        $scope.startcounter++;
			      }
		};
		
		$scope.stopSpin = function() {
		      if ($scope.spinneractive) {
		        usSpinnerService.stop('spinner-1');
		      }
		};
	
		$scope.spinneractive = false;

	    $rootScope.$on('us-spinner:spin', function(event, key) {
		      $scope.spinneractive = true;
	    });

	    $rootScope.$on('us-spinner:stop', function(event, key) {
		      $scope.spinneractive = false;
	    });
	    
	    var scope_options = AnalyticsCharts.getScopeOptions($scope);
		$scope = scope_options['scope'];
	
		function drawChart(chartTitle, chartName, chartType, systemType, chartFilters, $event) {
			$scope.showCarousel = false;
			$scope.showChart = true;
			$scope.stopSpin();
			$scope.startSpin();
			angular.element('.analytics-charts li div').removeClass('slick-selected');
			angular.element($event.currentTarget).parent().addClass(
			'slick-selected');
			$scope.data = [];
			$scope.pagination = { current: 1 };
			$scope.currentPage = 1;
			$scope.strict = false;
			$scope.notes = []; // remove stickies
			$scope.showLeads = false;
			
			$scope.chartName = chartName;
			$scope.chartTitle = chartTitle;
			$scope.chartType = chartType;
			$scope.systemType = systemType;
			$scope.options = '';
			$scope.groupDates = {};
			$scope.groupDates.date = {
					startDate : moment().subtract(6, "days").startOf("day"),
					endDate : moment().endOf("day")
			};
		
			
			$scope.startDate = $scope.groupDates.date.startDate;
			$scope.endDate = $scope.groupDates.date.endDate;
			
			
			
			$scope.clickOnNewChart = true; // when clicking on new chart
			$scope.filterBySource = false; // only true when filtering on source pie chart

			$scope.opts = {
					ranges : {
						'Last 7 days' : [ moment().subtract(6, "days"), moment() ],
						'Last 30 days' : [ moment().subtract(29, "days"), moment() ],
						'This Month' : [ moment().startOf("month"),
						                 moment().endOf("day") ]
					}
			};


			
			
			$scope.options = scope_options[chartName];
			$scope.options['chart'][chartType]['dispatch'] = {
					elementClick : function(e) {
						$scope.clickedElement = e;
						handleElementClick(e, false);
					}
			};

			$scope.config = {
					autorefresh : true
			};
			
			handleFilters(chartFilters);
			
			
		} // end of function chart
		//Analytics.retrieveChart('1', 'sources_bar', $scope.groupDates.date.startDate, $scope.groupDates.date.endDate).then(RetrieveAnalyticsSuccessFn, RetrieveAnalyticsErrorFn);
		
		
		
		function handleElementClick(e, fromPageChange) {
			
			$scope.filterBySource = false;
			$scope.filterByRevenueSource = false;
			$scope.filterByTweetInteractions = false;
			if (!fromPageChange)
			{
				$scope.pagination = { current: 1 };
				$scope.currentPage = 1;
			}
			
			if ($scope.chartName == "sources_bar")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					
					$scope.filterBySource = false;
					$scope.filterByRevenueSource = false;
					
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for '
						+ e.data.key + ' on ' + e.data.x //+ e.series.key + ' on ' + e.point.x
						+ ')';
					startDate = moment(e.data.x)
					.startOf('day').unix();
					endDate = moment(e.data.x).endOf('day')
					.unix();
					
					$scope.csv.functionToCall = Leads.getLeadsByFilter;
					$scope.csv.param[0] = account.company;
					$scope.csv.param[1] = e.data.key; //e.series.key;
					$scope.csv.param[2] = startDate;
					$scope.csv.param[3] = endDate;
					$scope.csv.param[4] = 'easy';
					$scope.csv.param[5] = 1;
					$scope.csv.param[6] = 1000000;
					$scope.csv.param[7] = $scope.systemType;
					
					Leads.getLeadsByFilter(account.company,
							e.data.key, startDate, endDate, 'easy', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName)
							.then(LeadsSuccessFn, LeadsErrorFn);
					
			    	
				}
			} // if sources_bar
			else if ($scope.chartName == "contacts_distr")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					
					$scope.filterBySource = false;
					$scope.filterByRevenueSource = false;
					
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for '
						+ e.point.label
						+ ')';
					startDate = $scope.startDate.unix();
					endDate = $scope.endDate.unix();
					
					$scope.csv.functionToCall = Leads.getLeadsByFilter;
					$scope.csv.param[0] = account.company;
					$scope.csv.param[1] = e.point.label;
					$scope.csv.param[2] = startDate;
					$scope.csv.param[3] = endDate;
					$scope.csv.param[4] = 'strict';
					$scope.csv.param[5] = 1;
					$scope.csv.param[6] = 1000000;
					$scope.csv.param[7] = $scope.systemType;
					
					Leads.getLeadsByFilterForDistribution(account.company,
							e.point.label, e.series.key, startDate, endDate, 'strict', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName)
							.then(LeadsSuccessFn, LeadsErrorFn);
				}
			} // if contacts_distr
			else if ($scope.chartName == "pipeline_duration") 
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					var startDate = 0;
					var endDate = 0;
					var series = '';
					var strict = '';
					if (e.series.key == 'Days in current status') // specifically for average duration
					{
						$scope.strict = true;
						strict = 'strict';
						series = numbers_to_labels[e.point.x];
					}
					else
					{
						$scope.strict = false;
						strict = '';
						series = $scope.statuses[e.point.x] + '-' + $scope.statuses[e.point.y]; //numbers_to_labels[e.seriesIndex];
					    $scope.status_series = {};
					    $scope.status_series['from'] = $scope.statuses[e.point.x];
					    $scope.status_series['to'] = $scope.statuses[e.point.y];
					}
						
					$scope.filterBySource = false;
					$scope.filterByRevenueSource = false;
					
					$scope.filterTitle = '(filtered for '
						+ series
						+ ')';
					startDate = $scope.startDate.unix();
					endDate = $scope.endDate.unix();
					
					$scope.csv.functionToCall = Leads.getLeadsByFilterDuration;
					$scope.csv.param[0] = account.company;
					$scope.csv.param[1] = series;
					$scope.csv.param[2] = startDate;
					$scope.csv.param[3] = endDate;
					$scope.csv.param[4] = strict;
					$scope.csv.param[5] = 1;
					$scope.csv.param[6] = 1000000;
					$scope.csv.param[7] = $scope.systemType;
					
					Leads.getLeadsByFilterDuration(account.company,
							series, startDate, endDate, strict, $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName)
							.then(LeadsWithDurationSuccessFn, LeadsErrorFn);
				}
			} //pipeline_duration
			
			else if ($scope.chartName == "source_pie")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for source '
					    + e.data.x //e.point.x 
						+ ')';
					$scope.filterBySource = true;
					$scope.filterByRevenueSource = false;
					startDate = $scope.startDate.unix();
					endDate = $scope.endDate.unix();

					$scope.csv.functionToCall = Leads.getLeadsBySourceChannel;
					$scope.csv.param[0] = account.company;
					$scope.csv.param[1] = e.data.x; //e.point.x;
					$scope.csv.param[2] = startDate;
					$scope.csv.param[3] = endDate;
					$scope.csv.param[4] = 'easy';
					$scope.csv.param[5] = 1;
					$scope.csv.param[6] = 1000000;
					$scope.csv.param[7] = $scope.systemType;
					
					Leads.getLeadsBySourceChannel(account.company,
							e.data.x, startDate, endDate, 'easy', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName)
							.then(LeadsSuccessFn, LeadsErrorFn);
					
			    	
				}
				
			} // if sources_bar
			
			else if ($scope.chartName == "revenue_source_pie")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for source '
					    + e.data.x
						+ ')';
					$scope.filterByRevenueSource = true;
					$scope.filterBySource = false;
					startDate = $scope.startDate.unix();
					endDate = $scope.endDate.unix();

					$scope.csv.functionToCall = Leads.getLeadsByRevenueSourceChannel;
					$scope.csv.param[0] = account.company;
					$scope.csv.param[1] = e.data.x;
					$scope.csv.param[2] = startDate;
					$scope.csv.param[3] = endDate;
					$scope.csv.param[4] = 'easy';
					$scope.csv.param[5] = 1;
					$scope.csv.param[6] = 1000000;
					$scope.csv.param[7] = $scope.systemType;
					
					Leads.getLeadsByRevenueSourceChannel(account.company,
							e.data.x, startDate, endDate, 'easy', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName)
							.then(LeadsSuccessFn, LeadsErrorFn);
					
			    	
				}
			} // if revenue_source_pie
			else if ($scope.chartName == "website_traffic") {
				toastr.info("No drilldown yet");
			} // if website traffic
			else if ($scope.chartName == "tw_performance")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					
					$scope.filterBySource = false;
					$scope.filterByRevenueSource = false;
					$scope.filterByTweetInteractions = true;
					
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for '
					    + e.data.x
						+ ')';
					startDate = moment(e.data.x)
					.startOf('day').unix();
					endDate = moment(e.data.x).endOf('day')
					.unix();
					
					Social.getTwInteractionsByFilter(account.company,
							e.data.key, startDate, endDate, 'easy', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName)
							.then(SocialSuccessFn, SocialErrorFn);
					
			    	
				}
			} // if tw_performance
			else if ($scope.chartName == "google_analytics")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					
					$scope.filterBySource = false;
					$scope.filterByRevenueSource = false;
					$scope.filterByTweetInteractions = true;
					
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for '
					    + e.data.x
						+ ')';
					startDate = moment(e.data.x)
					.startOf('day').unix();
					endDate = moment(e.data.x).endOf('day')
					.unix();
					
					Websites.getWebsitesByFilter(account.company,
							e.data.key, startDate, endDate, 'easy', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName, $scope.selectedFilterValues)
							.then(WebsitesSuccessFn, WebsitesErrorFn);
					
			    	
				}
			} // if google analytics
			else if ($scope.chartName == "facebook_organic_engagement")
			{
				var account = Authentication
				.getAuthenticatedAccount();
				if (account) {
					
					$scope.filterBySource = false;
					$scope.filterByRevenueSource = false;
					$scope.filterByTweetInteractions = false;
					
					var startDate = 0;
					var endDate = 0;
					$scope.filterTitle = '(filtered for '
					    + e.data.x
						+ ')';
					startDate = moment(e.data.x)
					.startOf('day').unix();
					endDate = moment(e.data.x).endOf('day')
					.unix();
					
					/* Websites.getWebsitesByFilter(account.company,
							e.data.key, startDate, endDate, 'easy', $scope.currentPage, $scope.leadsPerPage, $scope.systemType, $scope.chartName, $scope.selectedFilterValues)
							.then(WebsitesSuccessFn, WebsitesErrorFn); */
					
			    	
				}
			} // if google analytics
			
		} 
	
		
		$scope.pageChanged = function(newPage) {
			$scope.currentPage = newPage;
			handleElementClick($scope.clickedElement, true);
	    }
		
		$scope.$watch('groupDates.date', function(newDate, oldDate) { 
		//$scope.$watchGroup(['groupDates.date', 'selectedFilterValues'], function(newValues, oldValues, scope) { 
		//var newDate = newValues[0];
		//var oldDate = oldValues[0];
		if (!newDate || !oldDate) return;
		/*if ((oldDate != undefined) && ($scope.showChart) && (newDate != oldDate) && $scope.clickOnNewChart) // the chart is being clicked and the dates are different - can only happen if there were diff dates chosen on a previous chart
		*/
		if ($scope.clickOnNewChart === true && $scope.notFirstChart)
		{
			$scope.clickOnNewChart = false;
			return;
		}
		var startDate = 0;
		var endDate = 0;
		if ((newDate.startDate) && (newDate.endDate)
				&& (newDate != oldDate)) {
			startDate = moment(newDate.startDate).startOf('day');
			endDate = moment(newDate.endDate).endOf('day');
			$scope.startDate = startDate;
			$scope.endDate = endDate;
			var account = Authentication.getAuthenticatedAccount();
			$scope.data = [];
			//if ($scope.chartName != 'pipeline_duration')
			/*if ($scope.chartName == 'google_analytics') {
				$scope.data = [{values: [
				    {'date': '2015-07-01', 'high': 12, 'low': 2, 'open': 3, 'close':4},
				    {'date': '2015-07-02', 'high': 12, 'low': 6, 'open': 8, 'close':3},
				    {'date': '2015-07-03', 'high': 8, 'low': 1, 'open': 1, 'close':2},
				]}];
				$scope.showLeads = false;
				$scope.showTweets = false;
				$scope.showLeadsDuration = false;
				$scope.notFirstChart = true;
				$scope.clickOnNewChart = false;
			}
			else {*/
			Analytics.retrieveChart(account.company, $scope.chartName, startDate, endDate, $scope.systemType, $scope.selectedFilterValues)
			.then(RetrieveAnalyticsSuccessFn,
					RetrieveAnalyticsErrorFn);
		    //}
			//else
				//$scope.data = [{"key":"Stream0","values":[{"x":1,"y":10},{"x":2,"y":13},{"x":3,"y":18},{"x":4,"y":28},{"x":5,"y":19}],"type":"line","yAxis":1}, {"key":"Stream1","values":[{"x":1,"y":13},{"x":2,"y":10},{"x":3,"y":13},{"x":4,"y":20}],"type":"line","yAxis":1}, {"key":"Stream1","values":[{"x":1,"y":13},{"x":2,"y":10},{"x":3,"y":13},{"x":4,"y":20}],"type":"bar","yAxis":1}];

		}
	    }, true);
		
		$scope.$watch('selectedFilterValues', function(newFilter, oldFilter) { 
			if ($scope.clickOnNewChart === true && $scope.notFirstChart)
			{
				$scope.clickOnNewChart = false;
				return;
			}
			
			if (!$scope.groupDates || !$scope.groupDates.date) return;
			var newDate = $scope.groupDates.date;
			
			var startDate = moment(newDate.startDate).startOf('day');
			var endDate = moment(newDate.endDate).endOf('day');
			$scope.startDate = startDate;
			$scope.endDate = endDate;
			var account = Authentication.getAuthenticatedAccount();
			$scope.data = [];
			
			Analytics.retrieveChart(account.company, $scope.chartName, startDate, endDate, $scope.systemType, $scope.selectedFilterValues)
			.then(RetrieveAnalyticsSuccessFn,
					RetrieveAnalyticsErrorFn);
			
			
		}, true);
		
		function RetrieveAnalyticsSuccessFn(data, status, headers, config) {
			$scope.stopSpin();
			if (!data.data) {
				toastr.error("Oops! Something went wrong!");
				return false;
			}
			if (data.data["Error"]) {
				toastr.error(data.data["Error"]);
			} else {
				$scope.showLeads = false;
				$scope.showTweets = false;
				$scope.showLeadsDuration = false;
				$scope.showWebsiteVisitors = false;
				
				$scope.notFirstChart = true;
				$scope.clickOnNewChart = false;
				//if ($scope.chartName == "sources_bar" || $scope.chartName == "website_traffic" || $scope.chartName == "tw_performance" || $scope.chartName == "google_analytics") {
				if ($scope.chartType == 'multibar') {
				    $scope.data = data.data.map(function(d) {
						d.values = d.values.sort(AnalyticsCharts.natcmp);
						return d;
					});
				}
				else if ($scope.chartName == "pipeline_duration") {
					$scope.data = data.data.results;
					$scope.statuses = data.data.statuses;
				}
				else
					$scope.data = data.data;
				
			}
		}

		function RetrieveAnalyticsErrorFn(data, status, headers, config) {
			stopSpin();
			$scope.showLeads = false;
			$scope.showLeadsDuration = false;
			$scope.showTweets = false;
		}

		

		function LeadsSuccessFn(data, status, headers, config) {
			if (data.data.results) // they could contain  Mkto, SFDC or HSPT leads
			{
				$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
				
				vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, false, '', '');
				$scope.showLeads = true;
				$scope.showLeadsDuration = false;
				$scope.showTweets = false;
				$scope.showWebsiteVisitors = false;
				
				if (data.data.portal_id) { // drilldown into HSPT
					$scope.portal_id = data.data.portal_id;
					$scope.source_system = 'hspt';
					
				}
				
				$timeout(function() {
					$location.hash('leaddrilldown');
					$anchorScroll();
				}, 0);

				//$scope.$apply();
			} else {
				vm.leads = [];
				//$scope.showLeads = false;
			}
		}
		
		function LeadsWithDurationSuccessFn(data, status, headers, config) {
			if (data.data.results) // they could contain  Mkto, SFDC or HSPT leads
			{
				$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
				
				vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, true, $scope.status_series['from'], $scope.status_series['to']);
				$scope.showLeads = true;
				$scope.showLeadsDuration = true;
				$scope.showTweets = false;
				$scope.showWebsiteVisitors = false;
				
				$timeout(function() {
					$location.hash('leaddrilldown');
					$anchorScroll();
				}, 0);

				//$scope.$apply();
			} else {
				vm.leads = [];
				//$scope.showLeads = false;
			}
		}
		
		function LeadsErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Leads could not be retrieved');
		}
		
		function SocialSuccessFn(data, status, headers, config) {
			if (data.data.results) 
			{
				$scope.totalSocialInteractions = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startSocialCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
			    $scope.endSocialCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startSocialCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
				
				vm.interactions = data.data.results;
				for (var i=0; i < vm.interactions.length; i++) {
					vm.interactions[i].published_timestamp = moment.unix(vm.interactions[i].published_timestamp);
				}
				$scope.showTweets = true;
				$scope.showLeads = false;
				$scope.showLeadsDuration = false;
				$scope.showWebsiteVisitors = false;
				
				$timeout(function() {
					$location.hash('socialdrilldown');
					$anchorScroll();
				}, 0);

				//$scope.$apply();
			} else {
				vm.interactions = [];
				//$scope.showLeads = false;
			}
		}
		
		function SocialErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Social interactions could not be retrieved');
		}
		
		function WebsitesSuccessFn(data, status, headers, config) {
			if (data.data.results) 
			{
				$scope.totalWebsiteVisitors = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startWebsiteCounter = ($scope.currentPage - 1) * $scope.leadsPerPage + 1;
			    $scope.endWebsiteCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startWebsiteCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.leadsPerPage;
			    vm.websites = data.data.results;
				
				$scope.showWebsiteVisitors = true;
				$scope.showTweets = false;
				$scope.showLeads = false;
				$scope.showLeadsDuration = false;
				
				$timeout(function() {
					$location.hash('websitedrilldown');
					$anchorScroll();
				}, 0);

				//$scope.$apply();
			} else {
				vm.websites = [];
				//$scope.showLeads = false;
			}
		}
		
		function WebsitesErrorFn(data, status, headers, config) {
			// $location.url('/');
			toastr.error('Website visitors could not be retrieved');
		}


		
		
		function downloadLeadsCsv() {
			var params = '';
			for (var i=0; i < $scope.csv.param.length; i++)
				params+= $scope.csv.param[i] + ', ';
			
			$scope.csv.functionToCall($scope.csv.param[0], $scope.csv.param[1], $scope.csv.param[2], $scope.csv.param[3], $scope.csv.param[4], $scope.csv.param[5], $scope.csv.param[6], $scope.csv.param[7]).success(function(data, status, headers, config) {
				/*var csv = data.results.map(function(d) {
					return d.join();
				}).join('\n');*/
				var csv = toCsv(data.results);
				var anchor = angular.element('<a/>');
				anchor.attr({
					href: 'data:attachment/csv;charset=utf-8,' + encodeURI(csv),
					target: '_blank',
					download: 'leads.csv'
				})[0].click();
				toastr.success('CSV downloaded');
			}).error(function(data, status, headers, config) {
				toastr.error('Error while downloading CSV');
			});
			
			
		}

		function snapshot() {
			if (nv.tooltip && nv.tooltip.cleanup)
			   nv.tooltip.cleanup(); //hide the tooltip first to not dirty the HTML
			var chartHtml = '';
			chartHtml = angular.element(document.body).find('completearea')
			.html();
			//alert(chartHtml);
			var canvas, img, image = '';
			/*canvas = angular.element(document.querySelector('#svg-canvas'));
			window.canvg(canvas, chartHtml);*/
			/*img = angular.element(document.querySelector('#svg-img'));
			var base_image = new Image();
			chartHtml = "data:image/svg+xml," + chartHtml;
			base_image.src = chartHtml;*/
			//    		image = canvas.toDataUrl('image/png');
			//img.attr('src', chartHtml);
			var account = Authentication.getAuthenticatedAccount();
			if (account) {
				Snapshots.saveSnapshot(account.company, chartHtml,
						$scope.chartTitle).then(SaveSnapshotSuccessFn,
								SaveSnapshotErrorFn);
			}
		}

		function SaveSnapshotSuccessFn(data, status, headers, config) {
			if (data.data.message) {
				toastr.success(data.data.message);
				$scope.latestSnapshotId = data.data.snapshot.id;
			} else
				toastr.error(data.error);
		}

		function SaveSnapshotErrorFn(data, status, headers, config) {
			toastr.error(data.error);
		}

		

		//load canvg JS files
		var loadScript = function() {
			var script = document.createElement('script');
			script.type = 'text/javascript';
			script.src = 'http://canvg.googlecode.com/svn/trunk/rgbcolor.js';
			document.body.appendChild(script);
			script.src = 'http://canvg.googlecode.com/svn/trunk/canvg.js';
			document.body.appendChild(script);
			toastr.info('scripts loaded');
		}

		$scope.$on('$viewContentLoaded', function() {
			//loadScript();
		});

		function postToChannel() {
			$scope.subscribedRooms = $scope.$parent.subscribedRooms;

			var modalInstance = $modal
			.open({
				templateUrl : staticUrl('templates/messages/chart-message.html'),
				controller : modalController,
				scope : $scope,
				resolve : {
					rooms : function() {
						return $scope.subscribedRooms;
					},
				}
			//className: 'ngdialog-theme-default',
			//data: {channelId: channelId, name:name, description:description}
			});

			modalInstance.result.then(function(newMessage) {
				$scope.lastRoomId = newMessage.room.id;
				var account = Authentication.getAuthenticatedAccount();
				if (newMessage.snapshot === true) // if snapshot needs to be created first, do that
				{
					snapshot();

					$scope.$watch('latestSnapshotId', function(newId, oldId) {

						if (account && newId.length > 0) {
							Messages.submitMessage(account, newMessage.message,
									newMessage.room.id, newId).then(
											submitMessageSuccessFn,
											submitMessageErrorFn);
						}
					});
				} else {
					if (account) {
						Messages.submitMessage(account, newMessage.message,
								newMessage.room.id, '').then(
										submitMessageSuccessFn, submitMessageErrorFn);
					}
				}
			}, function() {

			});
		}

		function submitMessageSuccessFn(data, status, headers, config) {
			if (data.data["Error"]) {
				toastr.error(data.data["Error"]);
			} else {
				$scope.$parent.socket2.emit('user message', data.data.message,
						$scope.lastRoomId);
			}

		}

		function submitMessageErrorFn(data, status, headers, config) {

		}

		var modalController = function($scope, $modalInstance, rooms) {

			$scope.rooms = rooms;
			$scope.postedRoom = '';
			$scope.newMessage = {};
			$scope.submitForm = function(newMessage) {
				if ($scope.form.roomForm.$valid) {
					$modalInstance.close(newMessage);
				}
			};
			$scope.cancel = function() {
				$modalInstance.dismiss('cancel');
			};
		}
		
		/**
		* Converts a value to a string appropriate for entry into a CSV table.  E.g., a string value will be surrounded by quotes.
		* @param {string|number|object} theValue
		* @param {string} sDelimiter The string delimiter.  Defaults to a double quote (") if omitted.
		*/
		function toCsvValue(theValue, sDelimiter) {
			var t = typeof (theValue), output;
		 
			if (typeof (sDelimiter) === "undefined" || sDelimiter === null) {
				sDelimiter = '"';
			}
		 
			if (t === "undefined" || t === null) {
				output = "";
			} else if (t === "string") {
				output = sDelimiter + theValue + sDelimiter;
			} else {
				output = String(theValue);
			}
		 
			return output;
		}
		 
		/**
		* Converts an array of objects (with identical schemas) into a CSV table.
		* @param {Array} objArray An array of objects.  Each object in the array must have the same property list.
		* @param {string} sDelimiter The string delimiter.  Defaults to a double quote (") if omitted.
		* @param {string} cDelimiter The column delimiter.  Defaults to a comma (,) if omitted.
		* @return {string} The CSV equivalent of objArray.
		*/
		function toCsv(objArray, sDelimiter, cDelimiter) {
			var i, l, names = [], name, value, obj, row, output = "", n, nl;
		 
			// Initialize default parameters.
			if (typeof (sDelimiter) === "undefined" || sDelimiter === null) {
				sDelimiter = '"';
			}
			if (typeof (cDelimiter) === "undefined" || cDelimiter === null) {
				cDelimiter = ",";
			}
		 
			for (i = 0, l = objArray.length; i < l; i += 1) {
				// Get the names of the properties.
				obj = objArray[i];
				row = "";
				if (i === 0) {
					// Loop through the names
					for (name in obj) {
						if (obj.hasOwnProperty(name)) {
							if (typeof(obj[name]) === "object" && name == "leads") // if embedded object in array
							    if (obj[name]["hspt"]["properties"])
							{
								var newArray = obj[name]["hspt"]["properties"]; //JSON.parse(JSON.stringify(
								for (arrayName in newArray)
									if (newArray.hasOwnProperty(arrayName))
									names.push(arrayName)
							}
							names.push(name);
							row += [sDelimiter, name, sDelimiter, cDelimiter].join("");
						}
					}
					row = row.substring(0, row.length - 1);
					output += row;
				}
		 
				output += "\n";
				row = "";
				for (n = 0, nl = names.length; n < nl; n += 1) {
					name = names[n];
					value = obj[name];
					if (n > 0) {
						row += ","
					}
					row += toCsvValue(value, '"');
				}
				output += row;
			}
		 
			return output;
		}
		
		function handleFilters(chartFilters) {
			$scope.filters = {};
			$scope.filterValues = {};
			$scope.selectedFilterValues = {};
			$scope.requests = [];
			for (var i=0; i < chartFilters.length; i++) {
				$scope.filters[chartFilters[i]] = true;
				$scope.requests.push({"filterName": chartFilters[i]});
			}
			$q.all($scope.requests.map(function(request) {
        		return Analytics.getFilterMasterValues(account.company, request.filterName);
        	})).then(function(results){
        		var resultsPosition = 0;
        		for (var i=0; i < chartFilters.length; i++) {
    				$scope.filterValues[chartFilters[i]] = results[resultsPosition].data.results;
    				if (results[resultsPosition].data.defaultValue)
    				   $scope.selectedFilterValues[results[resultsPosition].data.defaultMetric] = results[resultsPosition].data.defaultValue;
    				resultsPosition++;
    			}
        	});
			
		}

	}
})();