/**
 * DashboardsController
 * 
 * @namespace mmm.dashboards.controllers
 */
(function() {
	'use strict';

	angular.module('mmm.dashboards.controllers', [ 'datatables' ]).controller(
			'DashboardsController', DashboardsController);

	DashboardsController.$inject = [ '$scope', 'Dashboards', 'Authentication',
	                                'Leads', 'Snapshots', '$location', 'DTOptionsBuilder',
	                                'DTColumnDefBuilder', 'DTColumnBuilder', 'DTInstances', '$filter',
	                                '$state', '$stateParams', '$document', '$window', 'Sticky',
	                                '$modal', 'Messages', '$anchorScroll', '$timeout', 'usSpinnerService', '$rootScope', 'Social', 'Websites', 'Common', 'Views', '$compile'];

	/**
	 * @namespace DashboardsController
	 */
	function DashboardsController($scope, Dashboards, Authentication, Leads,
			Snapshots, $location, DTOptionsBuilder, DTColumnDefBuilder,
			DTColumnBuilder, DTInstances, $filter, $state, $stateParams,
			$document, $window, Sticky, $modal, Messages, $anchorScroll, $timeout, usSpinnerService, $rootScope,  Social, Websites, Common, Views, $compile, $interval) {

		var vm = this;
		vm.dashboards = [];
		vm.leads = [];
		$scope.parseInt = parseInt;
		$scope.leads = [];
	    $scope.totalLeads = 0;
	    $scope.leadsPerPage = 10;
	    $scope.currentPageNumber = 1;
	    
	    vm.deals = [];
		$scope.deals = [];
	    $scope.totalDeals = 0;
	
		$scope.notes = [];
		$scope.createNote = createNote;
		$scope.deleteNote = deleteNote;
		$scope.handleDeletedNote = Sticky.handleDeletedNote;
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
		
		$scope.showLeads = false;
		$scope.showDeals = false;
		$scope.showLeadsDuration = false;
		$scope.showTweets = false;
		$scope.showWebsiteVisitors = false;
		$scope.showCarousel = true;
		$scope.showChart = false;
		$scope.notFirstChart = false; // this is set to false only when page is loaded else always true
		
		$scope.data = [];
		$scope.strict = false;
		/* $scope.chartName = ''; */
		$scope.chartType = '';
		$scope.startDate = '';
		$scope.endDate = '';
		$scope.selectedDateValue = 'dummy';
		$scope.snapshot = snapshot;
		/*$scope.staticUrl = staticUrl;
		$scope.drawChart = drawChart;*/
		$scope.postToChannel = postToChannel;
		$scope.barUrl = staticUrl('images/dashboards-bar.png');
		$scope.lineUrl = staticUrl('images/dashboards-line.png');
		$scope.rowUrl = staticUrl('images/dashboards-row.png');
		$scope.pieUrl = staticUrl('images/dashboards-pie.png');
		
		$scope.dashboardFunnelUrl = staticUrl('images/dashboard-funnel.png');
		$scope.drilldown = drilldown;
		
		$scope.portal_id = '';
		$scope.source_system = ''; 
		
		$scope.object = '';
    	$scope.section = '';
    	$scope.channel = '';
		
    	$scope.current_dashboard = '';
		$scope.dashboard_name = '';
		$scope.system_type = '';
		$scope.start_date = '';
		$scope.end_date = '';
		$scope.stageNames = {};
		$scope.stageNames = {'Assigned': 'Assigned', 'Blitz': 'Blitz', 'Marketing Nurture': 'Marketing Nurture', 'Open': 'Open', 'Qualified': 'Qualified', 'Unqualified': 'Unqualified', 'Working': 'Working', 'premql': 'Raw Leads', 'mql':'MQLs', 'sal':'SALs', 'sql': 'SQLs', 'opps': 'Deals', 'closedwon': 'Won', 'marketingqualifiedlead' : 'MQL', 'salesqualifiedlead' : 'SQL', 'customer' : 'Customer', 'subscriber' : 'Subscriber', 'lead' : 'Lead', 'opportunity' : 'Opportunity'};
		$scope.sourceNames = {'Advertising' : 'Advertising', 'Social Media': 'Social', 'Events': 'Events', 'Telemarketing': 'Telemarketing', 'Email': 'Email', 'Referral': 'Referral', 'Partner': 'Partner', 'Online': 'Online', 'Others': 'Others', 'Unknown': 'Unknown'};
		
		$scope.superFilterValues = {};
		$scope.selectedSuperFilterValues = {};
		$scope.selectedFilterValues = {};
		
		$scope.groupDates = {};
		$scope.groupDates.date = {
				startDate : moment().subtract(6, "days").startOf("day"),
				endDate : moment().endOf("day")
		};
		

		//$scope.system_type = 'MA';
		
		$scope.start_date = moment().subtract(30, "days").startOf("day").unix() * 1000;
		$scope.end_date = moment().endOf("day").unix() * 1000;
		$scope.results = {};
	
		
		$scope.startDate = $scope.groupDates.date.startDate;
		$scope.endDate = $scope.groupDates.date.endDate;
		$scope.opts = {
				ranges : {
					'Last 7 days' : [ moment().subtract(6, "days"), moment() ],
					'Last 30 days' : [ moment().subtract(29, "days"), moment() ],
					'This Month' : [ moment().startOf("month"),
					                 moment().endOf("day") ]
				},
				opens: 'left'
		};
		

		

		var account = Authentication.getAuthenticatedAccount();
		if (!account) {
			toastr.error('You need to login first');
			$location.url = '/login';
		}
		

		
		if ($state.params.name)
			$scope.dashboard_name = $state.params.name;
		
		/*if ($state.params.type == 'funnel') {
			$scope.dashboard_name = 'funnel';
		}
		else if ($state.params.type == 'social_roi') {
			$scope.dashboard_name = 'social_roi';
		}
		else if ($state.params.type == 'waterfall') {
			$scope.dashboard_name = 'waterfall';
		}
		else */
		if ($state.params.name == 'form_fills') {
			$scope.map = true;
			$scope.dashboard_name = 'form_fills';
			angular.extend($scope, {
				center: {
					lat: 40.8741,
					lng: 14.0625,
					zoom: 2
				},
				legend: {
                    colors: [ '#CC0066', '#006699', '#FF0000', '#00CC00', '#FFCC00' ],
                    labels: [ 'Oceania', 'America', 'Europe', 'Africa', 'Asia' ]
                },
                defaults: {
                	scrollWheelZoom: false
                }
			});
			
			Common.getCountriesData().then(CountriesDataSuccessFxn, CountriesDataErrorFxn);
		}
		
		getDashboards(); // get all dashboards for this company
		
		function getDashboards() {
	        var account = Authentication.getAuthenticatedAccount();
			if (account) {
			    Dashboards.getDashboardsByCompany(account.company)
					.then(DashboardsSuccessFn, DashboardsErrorFn);
			}
			else {
				toastr.error("You need to login first");
			}
        }
        
		function DashboardsSuccessFn(data, status, headers, config) {
			if (data.data.results.length > 0) 
			{  
				$scope.dashboards = data.data.results;
				$scope.current_dashboard = Common.findByAttr($scope.dashboards, 'name', $scope.dashboard_name);
				if ($scope.current_dashboard)
				{
					$scope.system_type = $scope.current_dashboard['system_type'];
					$scope.start_date = $scope.startDate;
					$scope.end_date = $scope.endDate;
					$scope.breadcrumbName = Common.capitalizeFirstLetter($scope.dashboard_name);
					$scope.showDashboard = true;
					$scope.notFirstDashboard = false;
					$scope.showDeals = false;
					$scope.showLeads = false;
					$scope.dashboardTitle = $scope.current_dashboard['title'];
					$scope.dashboardTemplate = $scope.current_dashboard['template'];
					$scope.template = staticUrl('templates/dashboards/' + $scope.dashboardTemplate);
					$scope.toolbar = staticUrl('templates/common/collab-toolbar.html');
					$scope.clickOnNewDashboard = true; // when clicking on new dashboard
					
					var account = Authentication.getAuthenticatedAccount();
					if (account) {
					   Views.getSuperFilters(account.company, $scope.current_dashboard['object'], $scope.current_dashboard['system_type']).then(SuperFiltersSuccessFxn, SuperFiltersErrorFxn);	
					}
					
				}
			}
			else {
				toastr.error("Could not find dashboards for company");
			}
		}
		
		function DashboardsErrorFn(data, status, headers, config) {
			toastr.error("Could not find dashboards for company");
			return false;
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
				// below lines to initialize dashboard and not let date watch trigger
				$scope.selectedDateValue = 'dummy';
				retrieveDashboard();
				/*for (var key in $scope.superFilterValues) { // sort descending
					if ($scope.superFilterValues.hasOwnProperty(key) && key != 'date_types') {
						$scope.superFilterValues[key]['values'].sort(function(a,b) {return (a.label > b.label)? 1: ((b.label > a.label)?-1:0);});
					}
				}*/
				
				/*$scope.groupDates.date = {
						startDate : moment().subtract(6, "days").startOf("day"),
						endDate : moment().endOf("day")
				};
			
				
				$scope.startDate = $scope.groupDates.date.startDate;
				$scope.endDate = $scope.groupDates.date.endDate;*/
			}
		}
		
        function SuperFiltersErrorFxn(data, status, headers, config) {
			
		}
		
		function DashboardSuccessFxn(data, status, headers, config) {
			$scope.stopSpin();
			//$scope.results = data.data;
			$scope.currentPage = {};
			$scope.currentPage.dashboardData = data.data; // these 2 lines needed to enable dashboard data in binders
			$scope.now = moment();
			$scope.selectedDateValue = 'dummy';
			if ($scope.map) // if showing a map, create markers
				createMarkers();
			/*$scope.start_date = $scope.results['start_date'];
			$scope.end_date = $scope.results['end_date'];
			$scope.created_source = $scope.results['created_source'];
			$scope.created_stage = $scope.results['created_stage'];
			$scope.existed_source = $scope.results['existed_source'];
			$scope.existed_stage = $scope.results['existed_stage'];*/
			
		}
		
        function DashboardErrorFxn(data, status, headers, config) {
        	$scope.stopSpin();
			toastr.error('Could not retrieve dashboard');
		}
        
        
        $scope.$watch('groupDates.date', function(newDate, oldDate) { 
    		if (!newDate || !oldDate) return;
    		if (newDate == oldDate) return;
    		if ($scope.clickOnNewDashboard) return; // if new dashboard let DashboardsSuccess call retrieveDB
    		if ($scope.system_type == undefined || $scope.system_type == '') return;
    		var startDate = 0;
    		var endDate = 0;
    		if ((newDate.startDate) && (newDate.endDate)
    				&& (newDate != oldDate)) {
    			startDate = moment(newDate.startDate).startOf('day').unix();
    			endDate = moment(newDate.endDate).endOf('day').unix();
    			//var startDate = moment(newDate.startDate).startOf('day');
    			//var endDate = moment(newDate.endDate).endOf('day');
    			$scope.startDate = startDate * 1000;
    			$scope.endDate = endDate * 1000;
    			$scope.start_date = startDate * 1000;
    			$scope.end_date = endDate * 1000;
    			$scope.showDeals = false;
				$scope.showLeads = false;
				/*if ($scope.current_dashboard)
					$scope.system_type = $scope.current_dashboard['system_type'];
				else
					$scope.system_type = 'MA';*/
				
				retrieveDashboard();
    			//Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type).then(DashboardSuccessFxn, DashboardErrorFxn);
    			
    		    
    		}
    	    }, true);
        
        
        $scope.$watch('selectedFilterValues', function(newFilter, oldFilter) { 
			
        	if (!newFilter || !oldFilter) return;
    		if (newFilter == oldFilter) return;
        	
        	if ($scope.clickOnNewDashboard === true && $scope.notFirstDashboard)
			{
				$scope.clickOnNewDashboard = false;
				return;
			}
			
			if (Object.keys(newFilter).length == 0 && Object.keys(oldFilter).length == 0) return;
			
			retrieveDashboard();
			
			
		}, true);
       
        
        
        function retrieveDashboard() {
        	var account = Authentication.getAuthenticatedAccount();
        	var filters = JSON.parse(JSON.stringify($scope.selectedFilterValues));
			filters = parseFilter(filters);
			
			$scope.clickOnNewDashboard = false;
			$scope.stopSpin();
			$scope.startSpin();
			
        	Dashboards.retrieveDashboard(account.company, $scope.dashboard_name, $scope.start_date, $scope.end_date, $scope.system_type, filters, $scope.selectedSuperFilterValues).then(DashboardSuccessFxn, DashboardErrorFxn);
    		
        }
        
        function drilldown(object, section, channel, chart_name) {
        	
        	$scope.object = object;
        	$scope.section = section;
        	$scope.channel = channel;
        	$scope.chart_name = chart_name;
        	//$scope.system_type = 'MA';
        	var filters = JSON.parse(JSON.stringify($scope.selectedFilterValues));
			filters = parseFilter(filters);
			$scope.stopSpin();
			$scope.startSpin();
        	
        	if (account)
        		{
        		   $scope.filterTitle = ' for ' + $scope.section.toUpperCase() + ' - ' + Common.capitalizeFirstLetter($scope.channel) + ' between ' + moment.unix($scope.start_date / 1000 ).format("YYYY-MM-DD") + ' and ' + moment.unix($scope.end_date / 1000).format("YYYY-MM-DD");
        		   if ($scope.object == 'contacts' || $scope.object == 'leads' || $scope.object == 'customers')
        		     Dashboards.drilldownContacts(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage).then(DrilldownContactsSuccessFxn, DrilldownErrorFxn);
        		   else if ($scope.object == 'deals'|| $scope.object == 'opps' )
        			   Dashboards.drilldownDeals(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage, filters, $scope.selectedSuperFilterValues).then(DrilldownDealsSuccessFxn, DrilldownErrorFxn);
        		}
        }
        
        function DrilldownContactsSuccessFxn(data, status, headers, config) {
        	if (data.data.results)
        	{
        		$scope.stopSpin();
	        	$scope.totalLeads = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				$scope.startLeadCounter = ($scope.currentPageNumber - 1) * $scope.leadsPerPage + 1;
			    $scope.endLeadCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startLeadCounter + $scope.thisSetCount -1 : $scope.currentPageNumber * $scope.leadsPerPage;
				
				vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, false, '', '');
				vm.leads.sort(Common.sortByProperty("id"));
				$scope.showLeads = true;
				$scope.showDeals = false;
				$scope.hideDetailColumn = true;
				if ($scope.chart_name == 'form_fills')
					$scope.showFormData = true;
				else
					$scope.showFormData = false;
				
				if (data.data.portal_id) { // drilldown into HSPT
					$scope.portal_id = data.data.portal_id;
					$scope.source_system = 'hspt';
					
				}
				
				$timeout(function() {
					$location.hash('leaddrilldown');
					$anchorScroll();
				}, 0);
        	}
        	else {
        		toastr.error('Could not retrieve drilldown');
        	}
		}
        
        function DrilldownDealsSuccessFxn(data, status, headers, config) {
        	if (data.data.results)
        	{
        		$scope.stopSpin();
        		$scope.totalDeals = data.data.count;
				$scope.thisSetCount = data.data.results.length;
				$scope.startDealCounter = ($scope.currentPageNumber - 1) * $scope.leadsPerPage + 1;
			    $scope.endDealCounter = ($scope.thisSetCount < $scope.leadsPerPage) ? $scope.startDealCounter + $scope.thisSetCount -1 : $scope.currentPageNumber * $scope.leadsPerPage;
				
				//vm.leads = Leads.cleanLeadsBeforeDisplay(data.data.results, false, '', '');
			    vm.deals = data.data.results;
			    $scope.multipleOccurs = false;
			    for (var i=0; i < vm.deals.length; i++)
			    	if (vm.deals[i]['multiple_occurences'])
			    	{
			    		$scope.multipleOccurs = true;
			    		break;
			    	}
			    		
				$scope.showDeals = true;
				$scope.showLeads = false;
				$scope.hideDetailColumn = true;
				
				if (data.data.portal_id) { // drilldown into HSPT
					$scope.portal_id = data.data.portal_id;
					$scope.source_system = 'hspt';
					
				}
				
				$scope.source_system = data.data.source_system;
				
				$timeout(function() {
					$location.hash('dealdrilldown');
					$anchorScroll();
				}, 0);
        	}
        	else {
        		toastr.error('Could not retrieve drilldown');
        	}
        }
        
        function DrilldownErrorFxn(data, status, headers, config) {
        	$scope.stopSpin();
			toastr.error('Could not retrieve drilldown');
		}
        
        $scope.pageChanged = function(newPage) {
			$scope.currentPageNumber = newPage;
			retrieveDashboard();
			$scope.stopSpin();
			$scope.startSpin();
			if (account)
	    		if ($scope.object == 'contacts' || $scope.object == 'leads' || $scope.object == 'customers')
	        	   Dashboards.drilldownContacts(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage).then(DrilldownContactsSuccessFxn, DrilldownErrorFxn);
	            else if ($scope.object == 'deals'|| $scope.object == 'opps' )
	        	   Dashboards.drilldownDeals(account.company, $scope.chart_name, $scope.object, $scope.section, $scope.channel, $scope.system_type, $scope.start_date, $scope.end_date, $scope.currentPageNumber, $scope.leadsPerPage, filters, $scope.selectedSuperFilterValues).then(DrilldownDealsSuccessFxn, DrilldownErrorFxn);
	        		
	    }
        
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
        
        //map related (for form fills) below
        
     // for form fills map
		$scope.map = false;
		 var continentProperties= {
	                "009": {
	                        name: 'Oceania',
	                        colors: [ '#CC0066', '#993366', '#990066', '#CC3399', '#CC6699' ]
	                },
	                "019": {
	                        name: 'America',
	                        colors: [ '#006699', '#336666', '#003366', '#3399CC', '#6699CC' ]
	                },
	                "150": {
	                        name: 'Europe',
	                        colors: [ '#FF0000', '#CC3333', '#990000', '#FF3333', '#FF6666' ]
	                },
	                "002": {
	                        name: 'Africa',
	                        colors: [ '#00CC00', '#339933', '#009900', '#33FF33', '#66FF66' ]
	                },
	                "142": {
	                        name: 'Asia',
	                        colors: [ '#FFCC00', '#CC9933', '#999900', '#FFCC33', '#FFCC66' ]
	                },
	        };
	        
	     // Get a country paint color from the continents array of colors
	        function getColor(country) {
	            if (!country || !country["region-code"]) {
	                return "#FFF";
	            }

	            var colors = continentProperties[country["region-code"]].colors;
	            var index = country["alpha-3"].charCodeAt(0) % colors.length ;
	            return colors[index];
	        }

	        
	        function style(feature) {
	            return {
	                fillColor: getColor($scope.countries[feature.id]),
	                weight: 2,
	                opacity: 1,
	                color: 'white',
	                dashArray: '3',
	                fillOpacity: 0.7
	            };
	        }
		 // end of form fills map
        
        function createMarkers() {
        	
        	//angular.extend($scope, {
        	$scope.markers = Dashboards.createMarkers($scope.currentPage.dashboardData.countries, $scope);
        	//$scope.layers = layers;
        	//});
        }
        
        function CountriesDataSuccessFxn(data, status, headers, config) {
        	
			$scope.countries = {};
            for (var i=0; i< data.data.length; i++) {
                var country = data.data[i];
                $scope.countries[country['alpha-3']] = country;
            }
            
            Common.getCountriesGeoData().then(CountriesGeoSuccessFxn, CountriesDataErrorFxn);	
        }
        
        function CountriesGeoSuccessFxn(data, status, headers, config) {
        	angular.extend($scope, {
                geojson: {
                    data: data.data,
                    style: style,
                    resetStyleOnMouseout: true
                },
                selectedCountry: {}
            }); 	
        }

        function CountriesDataErrorFxn(data, status, headers, config) {
        	
        	
        }
        
        // common functions
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
						$scope.dashboardTitle).then(SaveSnapshotSuccessFn,
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
		
	    

	}
})();