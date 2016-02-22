/**
 * ViewsController
 * 
 * @namespace mmm.views.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.views.controllers', [ 'datatables' ]).controller(
			'ViewsController', ViewsController);

	ViewsController.$inject = [ '$scope', 'Views', 'Authentication',
	                                'Leads', 'Campaigns', 'Accounts', 'Snapshots', '$location', 'DTOptionsBuilder',
	                                'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter',
	                                '$state', '$stateParams', '$document', '$window', 'Sticky',
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope', 'Social', 'Websites', '$q', 'Common'];

	/**
	 * @namespace ViewsController
	 */
	function ViewsController($scope, Views, Authentication, Leads, Campaigns, Accounts,
			Snapshots, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope, Social, Websites, $q, Common, $interval) {

		var vm = this;
		vm.views = [];
		vm.leads = [];
		$scope.leads = [];
	    $scope.totalLeads = 0;
	    $scope.rowsPerPage = 10;
	    $scope.currentPage = 1;
	
		$scope.notes = [];
		$scope.createNote = createNote;
		$scope.deleteNote = deleteNote;
		//$scope.handleDeletedNote = Sticky.handleDeletedNote;
		$scope.showView = false;
		$scope.notFirstView = false; // this is set to false only when page is loaded else always true
		
		$scope.data = [];
		$scope.strict = false;
		$scope.viewName = '';
		$scope.viewType = '';
		$scope.startDate = '';
		$scope.endDate = '';
		$scope.snapshot = snapshot;
		$scope.staticUrl = staticUrl;
		$scope.drawView = drawView;
		$scope.postToChannel = postToChannel;
		$scope.postToSlack = postToSlack;
		$scope.barUrl = staticUrl('images/views-bar.png');
		$scope.lineUrl = staticUrl('images/views-line.png');
		$scope.rowUrl = staticUrl('images/views-row.png');
		$scope.pieUrl = staticUrl('images/views-pie.png');
		
		$scope.filters = {};
		$scope.filterValues = {};
		//$scope.filterValues['campaign_guids'] = [];
		$scope.filterValuesFilled = {};
		$scope.filterValuesFilled['campaign_guids'] = false;
		$scope.selectedFilterValues = {};
		//$scope.selectedFilterValues['campaign_guid'] = '';
		$scope.superFilterValues = {};
		$scope.selectedSuperFilterValues = {};
		$scope.accountName = '';
		$scope.subviews = [];
		$scope.subview = {};
		$scope.subview['selectedSubview'] = '';
		
		/* functions for show/hide details */
		$scope.showingAccount = [];
	    for (var i=0, length = $scope.data.length; i < length; i++) {
	    	$scope.showingAccount[$scope.data[i].id] = false;
	    }
	    
	    $scope.showAccountDetails = function(account) {
	    	$scope.showingAccount[account.id] = true;
	    }
	    
	    $scope.hideAccountDetails = function(account) {
	    	$scope.showingAccount[account.id] = false;
	    }
	    
	    $scope.showingCompany = [];
	    for (var i=0, length = $scope.data.length; i < length; i++) {
	    	$scope.showingCompany[$scope.data[i]._id] = false;
	    }
	    
	    $scope.showCompanyDetails = function(account) {
	    	$scope.showingCompany[account._id] = true;
	    }
	    
	    $scope.hideCompanyDetails = function(account) {
	    	$scope.showingCompany[account._id] = false;
	    }
	    
	    /* end of functions for show/hide details */
	    
	    /* search and reset functions */
	    $scope.search = function() {
	    	if ($scope.viewName == 'accounts') {
		    	$scope.searchType = 'account';
		    	$scope.searchTerm = $scope.accountName; 
		    	searchByName();
	    	}
	    }
	    
	    $scope.resetSearch = function() {
	    	if ($scope.viewName == 'accounts') {
		    	$scope.accountName = '';
		    	$scope.mode = 'all-accounts';
		    	getAccounts(1);
	    	}
	    }
	    
	    /* end of search and reset functions */
		
		var account = Authentication.getAuthenticatedAccount();
		if (account) {
		    Views.getViewsByCompany(account.company)
				.then(ViewsSuccessFn, ViewsErrorFn);
		}
		else {
			toastr.error("You need to login first");
		}
		
		function ViewsSuccessFn(data, status, headers, config) {
			if (data.data.results.length > 0)  
			{ 
				$scope.views = data.data.results;
				/*for (var i=0; i < $scope.charts.length; i++)
					$scope.charts[i].src = staticUrl($scope.charts[i].src);*/
				if ($stateParams.name) // if being called for a specific view
				{
					var view = $scope.views.filter(function(obj) {
						return obj.name == $stateParams.name;
					});
					if (view[0])
					{
						$scope.viewName = view[0]['name'];
						$scope.subviews = view[0]['subviews'];
						if ($scope.subviews.length > 0) {
							$scope.subview['selectedSubview'] = $scope.subviews[0]['value'];
							$scope.subview['viewSubtitle'] = $scope.subviews[0]['name'];
						}
						
						drawView(view[0]['title'], view[0]['name'], view[0]['chart_type'], view[0]['system_type'], view[0]['template'], view[0]['filters']);
						var account = Authentication.getAuthenticatedAccount();
						if (account) {
						   Views.getSuperFilters(account.company, view[0]['object'], view[0]['system_type']).then(SuperFiltersSuccessFxn, SuperFiltersErrorFxn);	
						}
					}
					else
					   toastr.error("Oops! Could not create view!");	
				}
			}
			else {
				toastr.error("Could not find views for company");
			}
			//$scope.slackActive = $scope.$parent.slackActive;
		}
		
		function ViewsErrorFn(data, status, headers, config) {
			toastr.error("Could not find views for company");
			return false;
		} 
		
		
		
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
		 
		function drawView(viewTitle, viewName, viewType, systemType, viewTemplate, viewFilters) { //$event
			//var scope_options = Views.getScopeOptions($scope);
			//$scope = scope_options['scope'];
		
			$scope.showCarousel = false;
			$scope.showView = true;
			$scope.stopSpin();
			$scope.startSpin();
			//angular.element('.views-charts li div').removeClass('slick-selected');
			//angular.element($event.currentTarget).parent().addClass(
			//'slick-selected');
			$scope.data = [];
			$scope.pagination = { current: 1 };
			$scope.currentPage = 1;
			$scope.strict = false;
			$scope.notes = []; // remove stickies
			$scope.showLeads = false;
			
			$scope.viewTitle = viewTitle;
			$scope.viewName = viewName;
			$scope.viewType = viewType;
			$scope.systemType = systemType;
			$scope.template = staticUrl('templates/' + viewTemplate);
			$scope.toolbar = staticUrl('templates/common/collab-toolbar.html');
			$scope.viewFilters = viewFilters;
			
			$scope.options = '';
			$scope.groupDates = {};
			//moved the assignment of initial date values to SuperFiltersSuccessFxn
			
			
			
			$scope.clickOnNewView = true; // when clicking on new chart
			$scope.filterBySource = false; // only true when filtering on source pie chart

			$scope.opts = {
					ranges : {
						'Last 7 days' : [ moment().subtract(6, "days"), moment() ],
						'Last 30 days' : [ moment().subtract(29, "days"), moment() ],
						'This Month' : [ moment().startOf("month"),
						                 moment().endOf("day") ]
					}
			};


			
			
			/*$scope.options = scope_options[chartName];
			$scope.options['chart'][chartType]['dispatch'] = {
					elementClick : function(e) {
						$scope.clickedElement = e;
						handleElementClick(e, false);
					}
			};*/

			/*$scope.config = {
					autorefresh : true
			};*/
			
			handleFilters(viewFilters);
			
			
		} // end of function chart
		//Views.retrieveChart('1', 'sources_bar', $scope.groupDates.date.startDate, $scope.groupDates.date.endDate).then(RetrieveViewsSuccessFn, RetrieveViewsErrorFn);
		
		
		$scope.pageChanged = function(newPage) {
			$scope.currentPage = newPage;
			var account = Authentication.getAuthenticatedAccount();
			retrieveView();
			/*Views.retrieveView(account.company, $scope.viewName, $scope.startDate, $scope.endDate, $scope.systemType, $scope.currentPage, $scope.rowsPerPage, $scope.viewFilters, $scope.selectedSuperFilterValues, $scope.subview['selectedSubview'])
			.then(RetrieveViewSuccessFn,
					RetrieveViewErrorFn);*/
	    }
		
		$scope.$watch("selectedSuperFilterValues['date_types']", function(newDateType, oldDateType) {
			//if (!newDateType || !oldDateType) return;
			
			if (!$scope.groupDates || !$scope.groupDates.date) return;
			var newDate = $scope.groupDates.date;
			
			var startDate = moment(newDate.startDate).startOf('day');
			var endDate = moment(newDate.endDate).endOf('day');
			$scope.startDate = startDate;
			$scope.endDate = endDate;
			
			for (var i=0; i < $scope.superFilterValues['date_types'].length; i++) {
				if ($scope.superFilterValues['date_types'][i]['value'] == newDateType) {
					$scope.selectedDateType = $scope.superFilterValues['date_types'][i]['name'];
					$scope.selectedDateValue = $scope.superFilterValues['date_types'][i]['value'];
				    break;
			    }
			}
			
			var filters = JSON.parse(JSON.stringify($scope.selectedFilterValues));
			filters = parseFilter(filters);
			
			retrieveView();
			
			/*Views.retrieveView(account.company, $scope.viewName, startDate, endDate, $scope.systemType, $scope.currentPage, $scope.rowsPerPage, filters, $scope.selectedSuperFilterValues, $scope.subview['selectedSubview'])
			.then(RetrieveViewSuccessFn,
					RetrieveViewErrorFn);*/
		}, true);
		
		$scope.$watch('groupDates.date', function(newDate, oldDate) { 
		//$scope.$watchGroup(['groupDates.date', 'selectedFilterValues'], function(newValues, oldValues, scope) { 
		//var newDate = newValues[0];
		//var oldDate = oldValues[0];
		if (!newDate || !oldDate) return;
		/*if ((oldDate != undefined) && ($scope.showChart) && (newDate != oldDate) && $scope.clickOnNewChart) // the chart is being clicked and the dates are different - can only happen if there were diff dates chosen on a previous chart
		*/
		if ($scope.clickOnNewView === true && $scope.notFirstView)
		{
			$scope.clickOnNewView = false;
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
			
            var filters = JSON.parse(JSON.stringify($scope.selectedFilterValues));
			filters = parseFilter(filters);
			
			retrieveView();
			/*Views.retrieveView(account.company, $scope.viewName, startDate, endDate, $scope.systemType, $scope.currentPage, $scope.rowsPerPage, filters, $scope.selectedSuperFilterValues, $scope.subview['selectedSubview'])
			.then(RetrieveViewSuccessFn,
					RetrieveViewErrorFn);*/
		    //}
			//else
				//$scope.data = [{"key":"Stream0","values":[{"x":1,"y":10},{"x":2,"y":13},{"x":3,"y":18},{"x":4,"y":28},{"x":5,"y":19}],"type":"line","yAxis":1}, {"key":"Stream1","values":[{"x":1,"y":13},{"x":2,"y":10},{"x":3,"y":13},{"x":4,"y":20}],"type":"line","yAxis":1}, {"key":"Stream1","values":[{"x":1,"y":13},{"x":2,"y":10},{"x":3,"y":13},{"x":4,"y":20}],"type":"bar","yAxis":1}];

		}
	    }, true);
		
		$scope.$watch('selectedFilterValues', function(newFilter, oldFilter) { 
			if ($scope.clickOnNewView === true && $scope.notFirstView)
			{
				$scope.clickOnNewView = false;
				return;
			}
			
			if (Object.keys(newFilter).length == 0 && Object.keys(oldFilter).length == 0) return;
			
			retrieveView();
			
			
		}, true);
		
		$scope.$watch('subview.selectedSubview', function(newSubview, oldSubview) { 
			if ($scope.clickOnNewView === true && $scope.notFirstView)
			{
				$scope.clickOnNewView = false;
				return;
			}
			
			if (!newSubview || !oldSubview) return;
			
			for (var i=0; i < $scope.subviews.length; i++) {
				if ($scope.subviews[i]['value'] == $scope.subview['selectedSubview'])
				{
					$scope.subview['viewSubtitle'] = $scope.subviews[i]['name'];
					break;
				}
			}
			
			retrieveView();
			
			
		}, true);
		
		function parseFilter(filters) {
			// do this dance because of the acute plugin sending both id and name for the filter selected value
			for (var key in $scope.selectedFilterValues) {
				if ($scope.selectedFilterValues.hasOwnProperty(key)) {
					var obj = $scope.selectedFilterValues[key];
					for (var prop in obj) {
						if (obj.hasOwnProperty(prop) && prop == 'id')
							filters[key] = $scope.selectedFilterValues[key]['id'];
					}
				}
			}
			return filters;
		}
		
		function RetrieveViewSuccessFn(data, status, headers, config) {
			$scope.stopSpin();
			$scope.duplicate = false;
			
			if (!data.data) {
				toastr.error("Oops! Something went wrong!");
				return false;
			}
			if (data.data["Error"]) {
				toastr.error(data.data["Error"]);
			} else {
				$scope.showView = true;
				
				$scope.notFirstChart = true;
				$scope.clickOnNewChart = false;
				//if ($scope.chartName == "sources_bar" || $scope.chartName == "website_traffic" || $scope.chartName == "tw_performance" || $scope.chartName == "google_views") {
				$scope.others = {}
				if (data.data.type && data.data.type == 'contacts')
				   $scope.data = Leads.cleanLeadsBeforeDisplay(data.data.results);
				else if (data.data.type && data.data.type == 'duplicate-contacts')
				{
					   $scope.data = Leads.cleanDuplicateLeadsBeforeDisplay(data.data.results);
					   $scope.duplicate = true;
				}
				else
				   $scope.data = data.data.results;
				$scope.source_system = data.data.source_system;
				$scope.hideDetailColumn = true;
				$scope.totalCount = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startCounter = ($scope.currentPage - 1) * $scope.rowsPerPage + 1;
			    $scope.endCounter = ($scope.thisSetCount < $scope.rowsPerPage) ? $scope.startCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.rowsPerPage;
				// if there are other metrics, add them to the scope
			    if (data.data.others) {
			    	for (var key in data.data.others) {
		    			if (data.data.others.hasOwnProperty(key)) {
		    				$scope.others[key] = data.data.others[key];
		    			}
			        }
			    }
				
				$scope.now = moment();
				
			}
		}

		function RetrieveViewErrorFn(data, status, headers, config) {
			stopSpin();
			$scope.showView = false;
		}

		function SuperFiltersSuccessFxn(data, status, headers, config) {
			$scope.showFilters = false;
			if (data.data.results) {
				for (var key in data.data.results) {
	    			if (data.data.results.hasOwnProperty(key)) {
	    				$scope.superFilterValues[key] = data.data.results[key];
	    				$scope.showFilters = true;
	    			}
		        }
				for (var key in $scope.superFilterValues) {
	    			if ($scope.superFilterValues.hasOwnProperty(key)) {
	    			   var obj = $scope.superFilterValues[key][0];
				       if (key == 'date_types') {
				    	   $scope.selectedSuperFilterValues[key] = obj[Object.keys(obj)[1]];
				    	   $scope.selectedDateType = obj[Object.keys(obj)[0]];
				           $scope.selectedDateValue = obj[Object.keys(obj)[1]];
				       }
	    			}
				}
				
				$scope.groupDates.date = {
						startDate : moment().subtract(6, "days").startOf("day"),
						endDate : moment().endOf("day")
				};
			
				
				$scope.startDate = $scope.groupDates.date.startDate;
				$scope.endDate = $scope.groupDates.date.endDate;
			}
		}
		
        function SuperFiltersErrorFxn(data, status, headers, config) {
			
		}

		function LeadsSuccessFn(data, status, headers, config) {
			if (data.data.results) // they could contain  Mkto, SFDC or HSPT leads
			{
				$scope.stopSpin();
				$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.rowsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.rowsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.rowsPerPage;
				
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
				$scope.stopSpin();
				$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.rowsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.rowsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.rowsPerPage;
				
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
			$scope.stopSpin();
			toastr.error('Contact details could not be retrieved');
		}
		
		function CampaignsSuccessFn(data, status, headers, config) {
			if (data.data.results) 
			{
				$scope.stopSpin();
				$scope.totalCampaigns = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startLeadCounter = ($scope.currentPage - 1) * $scope.rowsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.rowsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.rowsPerPage;
				
				vm.campaigns = data.data.results;
				$scope.showCampaigns = true;
				$scope.showLeads = false;
				$scope.showLeadsDuration = false;
				$scope.showTweets = false;
				$scope.showWebsiteVisitors = false;
				
				if (data.data.portal_id) { // drilldown into HSPT
					$scope.portal_id = data.data.portal_id;
					$scope.source_system = 'hspt';
				}
				
				$timeout(function() {
					$location.hash('campaigndrilldown');
					$anchorScroll();
				}, 0);

				//$scope.$apply();
			} else {
				vm.campaigns = [];
				//$scope.showLeads = false;
			}
		}
		
		function CampaignsErrorFn(data, status, headers, config) {
			// $location.url('/');
			$scope.stopSpin();
			toastr.error('Campaign details could not be retrieved');
		}
		
		function SocialSuccessFn(data, status, headers, config) {
			if (data.data.results) 
			{
				$scope.stopSpin();
				$scope.totalSocialInteractions = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startSocialCounter = ($scope.currentPage - 1) * $scope.rowsPerPage + 1;
			    $scope.endSocialCounter = ($scope.thisSetCount < $scope.rowsPerPage) ? $scope.startSocialCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.rowsPerPage;
				
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
			$scope.stopSpin();
			toastr.error('Social interactions could not be retrieved');
		}
		
		function WebsitesSuccessFn(data, status, headers, config) {
			if (data.data.results) 
			{
				$scope.stopSpin();
				$scope.totalWebsiteVisitors = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				// initialize the start and end counts shown near pagination control
				$scope.startWebsiteCounter = ($scope.currentPage - 1) * $scope.rowsPerPage + 1;
			    $scope.endWebsiteCounter = ($scope.thisSetCount < $scope.rowsPerPage) ? $scope.startWebsiteCounter + $scope.thisSetCount -1 : $scope.currentPage * $scope.rowsPerPage;
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
			$scope.stopSpin();
			toastr.error('Website visitors could not be retrieved');
		}


		
		
		function downloadLeadsCsv() {
			if ($scope.csv.param[$scope.csv.param.length - 1] != 'csv') // add this parameter to indicate to the backend that this is a CSV
			   $scope.csv.param[$scope.csv.param.length] = 'csv';
			$scope.csv.functionToCall.apply(this, $scope.csv.param).then(CsvDownloadSuccessFxn, CsvDownloadErrorFxn);
			
			/*$scope.csv.functionToCall($scope.csv.param[0], $scope.csv.param[1], $scope.csv.param[2], $scope.csv.param[3], $scope.csv.param[4], $scope.csv.param[5], $scope.csv.param[6], $scope.csv.param[7]).success(function(data, status, headers, config) {
				var csv = data.results.map(function(d) {
					return d.join();
				}).join('\n');
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
			});*/
			
			
		}
	
	    function CsvDownloadSuccessFxn(data, status, headers, config) {
	    	toastr.info('Export to CSV is scheduled. Check My Exports for details');
	    }
	    
	    function CsvDownloadErrorFxn(data, status, headers, config) {
	    	toastr.error('Export to CSV could not be scheduled');
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
						$scope.viewTitle).then(SaveSnapshotSuccessFn,
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
					$scope.latestSnapshotId = '';
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
				toastr.success("Message posted!");
				$scope.$parent.socket2.emit('user message', data.data.message,
						$scope.lastRoomId);
			}

		}

		function submitMessageErrorFn(data, status, headers, config) {

		}
		
		function postToSlack() {
			$scope.slack_channels = $scope.$parent.slack_channels;
			$scope.slack_groups = $scope.$parent.slack_groups;
			$scope.slack_ims = $scope.$parent.slack_ims;

			var modalInstance = $modal
			.open({
				templateUrl : staticUrl('templates/messages/chart-slack-message.html'),
				controller : modalSlackController,
				scope : $scope,
				resolve : {
					slack_groups : function() {
						return $scope.slack_groups;
					},
					slack_channels : function() {
						return $scope.slack_channels;
					},
					slack_ims : function() {
						return $scope.slack_ims;
					},
				}
			//className: 'ngdialog-theme-default',
			//data: {channelId: channelId, name:name, description:description}
			});

			modalInstance.result.then(function(slackMessage) {
				$scope.slackOption = slackMessage.option.type;
				$scope.slackChannel = slackMessage.channel.id;
				var account = Authentication.getAuthenticatedAccount();
				if (slackMessage.snapshot === true) // if snapshot needs to be created first, do that
				{
					$scope.latestSnapshotId = '';
					snapshot();

					$scope.$watch('latestSnapshotId', function(newId, oldId) {

						if (account && newId.length > 0) {
							Messages.submitSlackMessage(account.company, slackMessage.message, slackMessage.channel.id, newId).then(
											submitSlackMessageSuccessFn,
											submitSlackMessageErrorFn);
						}
					});
				} else {
					if (account) {
						var newMessage = {}
						newMessage.text = slackMessage.message;
						newMessage.channel = slackMessage.channel.id;
						newMessage.type = 'message';
						newMessage.id = moment().unix();
						$rootScope.slackSocket.send(newMessage);
						//newMessage.ts = newMessage.id;
						//newMessage.user = $scope.slackUser;
						//newMessage.text = formatSlackMsg(newMessage.text, false);
		            	//newMessage = Messages.formatSlackUserInfo(newMessage, $scope.slack_users);
		            	//$scope.slack_messages.push(newMessage);
					}
				}
			}, function() {

			});
		}
		
		function submitSlackMessageSuccessFn(data, status, headers, config) {
			if (data.data["Error"]) {
				toastr.error(data.data["Error"]);
			} else {
				toastr.success("Message posted to Slack!");
			}

		}

		function submitSlackMessageErrorFn(data, status, headers, config) {

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
		
		var modalSlackController = function($scope, $modalInstance, slack_groups, slack_channels, slack_ims) {

			$scope.slack_groups = slack_groups;
			$scope.slack_channels = slack_channels;
			$scope.slack_ims = slack_ims;
			$scope.postedRoom = '';
			$scope.slackMessage = {};
			$scope.submitForm = function(slackMessage) {
				if ($scope.form.roomForm.$valid) {
					$modalInstance.close(slackMessage);
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
			
			$scope.requests = [];
			for (var i=0; i < chartFilters.length; i++) {
				$scope.filters[chartFilters[i]] = true;
				$scope.requests.push({"filterName": chartFilters[i]});
			}
			$q.all($scope.requests.map(function(request) {
        		return Views.getFilterMasterValues(account.company, request.filterName);
        	})).then(function(results){
        		var resultsPosition = 0;
        		for (var i=0; i < chartFilters.length; i++) {
    				$scope.filterValues[chartFilters[i]] = results[resultsPosition].data.results;
    				$scope.filterValues[chartFilters[i]].sort(Common.sortByProperty("name"));
    				$scope.filterValuesFilled[chartFilters[i]] = true;
    				if (results[resultsPosition].data.defaultValue)
    				   $scope.selectedFilterValues[results[resultsPosition].data.defaultMetric] = results[resultsPosition].data.defaultValue;
    				resultsPosition++;
    			}
        	});
			
		}
		
		function searchByName() {
	    	var trimmedName = $scope.searchTerm.trim();
	    	if (trimmedName.length ==  0)
	    	{   
	    		$scope.mode = 'all-accounts';
	    		retrieveView();
	    	}
	    	else if (trimmedName.length < 3) {
	    		toastr.error('Please enter at least 3 letters to search');
	    		return false;
	    	}
	    	var account = Authentication.getAuthenticatedAccount();
		    if (account && $scope.searchType == 'account') {
		    	$scope.mode = 'search-accounts';
		    	Accounts.matchAccountName(account.company, trimmedName, $scope.currentPage, $scope.accountsPerPage).then(RetrieveViewSuccessFn, RetrieveViewErrorFn);
		    }
	    }
		
		function retrieveView() {
			var account = Authentication.getAuthenticatedAccount();
			$scope.data = [];
			$scope.stopSpin();
			$scope.startSpin();
			
			var filters = JSON.parse(JSON.stringify($scope.selectedFilterValues));
			filters = parseFilter(filters);
			
			//$scope.currentPage = 1;
			
			Views.retrieveView(account.company, $scope.viewName, $scope.startDate, $scope.endDate, $scope.systemType, $scope.currentPage, $scope.rowsPerPage, filters, $scope.selectedSuperFilterValues, $scope.subview['selectedSubview'])
			.then(RetrieveViewSuccessFn,
					RetrieveViewErrorFn);
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
	    

	}
})();