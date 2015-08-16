/**
* AnalyticsCharts
* @namespace mmm.analytics.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.analytics.services')
    .factory('AnalyticsCharts', AnalyticsCharts);

  AnalyticsCharts.$inject = ['$http'];

  /**
  * @namespace AnalyticsCharts
  * @returns {Factory}
  */
  function AnalyticsCharts($http) {
    var AnalyticsCharts = {
      getScopeOptions: getScopeOptions,
      natcmp: natcmp
      
    };

    return AnalyticsCharts;
    
    function strcmp(a, b) {
		return a > b ? -1 : a < b ? 1 : 0;
	}

	
    
    function getScopeOptions($scope) {
	    var scope_options = {};
	    scope_options.sources_bar = {
				chart : {
					type : 'multiBarChart',
					height : 450,
					margin : {
						top : 20,
						right : 20,
						bottom : 60,
						left : 45
					},
					clipEdge : true,
					staggerLabels : false,
					transitionDuration : 500,
					stacked : false,
					xAxis : {
						//axisLabel: 'Date',
						/*axisLabelDistance: 200,
				showMaxMin: false,
				margin: {
					top: 0,
					right:0, 
					bottom:0,
					left:0
				}*/
						/*tickFormat: function(d){
				    return d3.format(',f')(d);
				}*/
					},
					yAxis : {
						axisLabel : 'Number',
						axisLabelDistance : 40,
						tickFormat : function(d) {
							return d3.format(',f')(d);
						}
					},
					tooltip: {
						contentGenerator : function(input) { //key, x, y, e, graph
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ input.data.key
						+ '</h4>'
						+ '<p>'
						+ input.data.y
						+ ' on '
						+ input.data.x
						+ '</p></div>'
						}
					},
					multibar : {
						/*dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);	
							}
						}*/
					},
					legend : {
	
					}
	
				},
				title : {
					enable : true,
					text : 'Timeline by Stage Date'
				}
	
		};
	
		scope_options.contacts_distr = {
	            chart: {
	                type: 'multiBarHorizontalChart',
	                height: 450,
	                margin : {
	                    top: 20,
	                    right: 20,
	                    bottom: 60,
	                    left: 100
	                },
	                x: function(d){return d.label;},
	                y: function(d){return d.value;},
	                showValues: false,
	                showLegend: true,
	                showControls: true,
	                valueFormat: function(d){
	                    return d3.format(',f')(d);
	                },
	                transitionDuration: 500,
	                xAxis: {
	                    axisLabel: '',
	                    
						
	                },
	                yAxis : {
						/*axisLabel : 'Number',
						axisLabelDistance : 40,
						tickFormat : function(d) {
							return d3.format(',f')(d);
						}*/
	                	tickFormat : function(d) {
							return d3.format(',f')(d);
						},
	                
					},
	                tooltipContent : function(key, x, y, e, graph) {
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ key
						+ '</h4>'
						+ '<p>'
						+ y
						+ ' on '
						+ x
						+ '</p></div>'
					},
					multibar : {
					/*	dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);
							}
						}*/
					},
					legend : {
	
					}
	            },
				title : {
					enable : true,
					text : 'Contacts Distribution by Stage Date'
				}
	        };
		
	/*		var numbers_to_labels = ['Subscribers', 'Leads', 'MQLs', 'SQLs', 'Opportunities', 'Customers', "All"];
		scope_options.pipeline_duration = {
				chart: {
	                type: 'lineChart',
	                height: 450,
	                margin : {
	                    top: 30,
	                    right: 60,
	                    bottom: 50,
	                    left: 70
	                },
	                color: d3.scale.category10().range(),
	                //useInteractiveGuideline: true,
	                transitionDuration: 500,
	                useInteractiveGuideline: false,
	                xAxis: {
	                	tickValues: [0, 1, 2, 3, 4, 5],
	                    tickFormat: function(d) {
	                    	return numbers_to_labels[d]
	                    },
	                    showMaxMin: true,
	                    //width: 500
	                },
	                yAxis: {
	                    tickFormat: function(d){
	                        return d3.format(',.1f')(d);
	                    }
	                },
					tooltipContent : function(key, x, y, e, graph) { 
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ key
						+ '</h4>'
						+ '<p>'
						+ y
						+ ' on '
						+ x
						+ '</p></div>'
					},
					lines : {
						clipVoronoi: false,
						useVoronoi: false,
						dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);
							}
						}
					},
					legend : {
	
					}
	            },
				title : {
					enable : true,
					text : 'Pipeline Duration by Stage Date'
				}
	  
	        };*/
		
		var numbers_to_labels = ['Subscribers', 'Leads', 'MQLs', 'SQLs', 'Opportunities', 'Customers', "All"];
		scope_options.pipeline_duration = {
				chart: {
	                type: 'scatterChart',
	                height: 450,
	                margin : {
	                    top: 30,
	                    right: 60,
	                    bottom: 50,
	                    left: 70
	                },
	                color: d3.scale.category10().range(),
	                //useInteractiveGuideline: true,
	                transitionDuration: 500,
	                useInteractiveGuideline: false,
	                xAxis: {
	                	tickFormat: function(d) {
	                    	return $scope.statuses[d]
	                    },
	                    showMaxMin: true,
	                    //width: 500
	                },
	                yAxis: {
	                	tickFormat: function(d) {
	                    	return $scope.statuses[d]
	                    }
	                },
					tooltipContent : function(key, x, y, e, graph) { 
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ e.point.changes + ' leads took on an average '
						+ e.point.size 
						+ ' days from </h4>'
						+ '<p>'
						+ x
						+ ' to '
						+ y
						+ '</p></div>'
					},
					scatter : {
						onlyCircles: true,
						useVoronoi: false,
						clipVoronoi: false,
						/*dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);
							}
						}*/
					},
					legend : {
	
					}
	            },
				title : {
					enable : true,
					text : 'Pipeline Duration by Stage Date'
				}
	  
	        };
		
		scope_options.source_pie = {
	            chart: {
	                type: 'pieChart',
	                height: 450,
	                margin : {
	                    top: 20,
	                    right: 20,
	                    bottom: 60,
	                    left: 100
	                },
	                showValues: true,
	                showLegend: true,
	                legend: {
	                	 margin : {
	 	                    top: 20,
	 	                    right: 20,
	 	                    bottom: 60,
	 	                    left: 100
	 	                },
	                	width: 500,
	                	align: true,
	                	rightAlign: true
	                },
	                showControls: false,
	                transitionDuration: 500,
	                tooltip: {
						contentGenerator : function(input) { //key, x, y, e, graph
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ input.data.x
						+ '</h4>'
						+ '<p>'
						+ input.data.y
						+ '</p></div>'
						}
					},
					pie : {
/*						dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);
							}
						},*/
						labelType: 'percent'
					},
					growOnHover: true,
					tooltips: true,
					legend : {
	
					}
	            },
				title : {
					enable : true,
					text : 'Leads by Source based on Creation Date'
				}
	        };
		
		scope_options.revenue_source_pie = {
	            chart: {
	                type: 'pieChart',
	                height: 450,
	                margin : {
	                    top: 20,
	                    right: 20,
	                    bottom: 60,
	                    left: 100
	                },
	                showValues: true,
	                showLegend: true,
	                legend: {
	                	 margin : {
	 	                    top: 20,
	 	                    right: 20,
	 	                    bottom: 60,
	 	                    left: 100
	 	                },
	                	width: 500,
	                	align: true,
	                	rightAlign: true
	                },
	                showControls: false,
	                transitionDuration: 500,
	                tooltip: {
						contentGenerator : function(input) { //key, x, y, e, graph
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ input.data.x
						+ '</h4>'
						+ '<p>'
						+ input.data.y
						+ '</p></div>'
						}
					},
					pie : {
						/*dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);
							}
						},*/
						labelType: 'percent'
					},
					growOnHover: true,
					tooltips: true,
					legend : {
	
					}
	            },
				title : {
					enable : true,
					text : 'Revenue by Source Channel'
				}
	        };
		
		scope_options.website_traffic = {
				chart : {
					type : 'multiBarChart',
					height : 450,
					margin : {
						top : 20,
						right : 20,
						bottom : 60,
						left : 45
					},
					clipEdge : true,
					staggerLabels : false,
					transitionDuration : 500,
					stacked : false,
					xAxis : {
						//axisLabel: 'Date',
						/*axisLabelDistance: 200,
				showMaxMin: false,
				margin: {
					top: 0,
					right:0, 
					bottom:0,
					left:0
				}*/
						/*tickFormat: function(d){
				    return d3.format(',f')(d);
				}*/
					},
					yAxis : {
						axisLabel : 'Number',
						axisLabelDistance : 40,
						tickFormat : function(d) {
							return d3.format(',f')(d);
						}
					},
					tooltip: {
						contentGenerator : function(input) { //key, x, y, e, graph
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ input.data.key
						+ '</h4>'
						+ '<p>'
						+ input.data.y
						+ ' on '
						+ input.data.x
						+ '</p></div>'
						}
					},
					multibar : {
						/*dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);	
							}
						}*/
					},
					legend : {
	
					}
	
				},
				title : {
					enable : true,
					text : 'Website Traffic by Source'
				}
	
		};
		
		scope_options.tw_performance = {
				chart : {
					type : 'multiBarChart',
					height : 450,
					margin : {
						top : 20,
						right : 20,
						bottom : 60,
						left : 45
					},
					clipEdge : true,
					staggerLabels : false,
					transitionDuration : 500,
					stacked : false,
					xAxis : {
						//axisLabel: 'Date',
						/*axisLabelDistance: 200,
				showMaxMin: false,
				margin: {
					top: 0,
					right:0, 
					bottom:0,
					left:0
				}*/
						/*tickFormat: function(d){
				    return d3.format(',f')(d);
				}*/
					},
					yAxis : {
						axisLabel : 'Number',
						axisLabelDistance : 40,
						tickFormat : function(d) {
							return d3.format(',f')(d);
						}
					},
					tooltip: {
						contentGenerator : function(input) { //key, x, y, e, graph
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ input.data.key
						+ '</h4>'
						+ '<p>'
						+ input.data.y
						+ ' on '
						+ input.data.x
						+ '</p></div>'
						}
					},
					multibar : {
						/*dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);	
							}
						}*/
					},
					legend : {
	
					}
	
				},
				title : {
					enable : true,
					text : 'Performance of Tweets'
				}
	
		};
		
		scope_options.google_analytics = {
				chart : {
					type : 'multiBarChart',
					height : 450,
					margin : {
						top : 20,
						right : 20,
						bottom : 60,
						left : 45
					},
					clipEdge : true,
					staggerLabels : false,
					transitionDuration : 500,
					stacked : false,
					xAxis : {
						
					},
					yAxis : {
						axisLabel : 'Visitors',
						axisLabelDistance : 40,
						tickFormat : function(d) {
							return d3.format(',f')(d);
						}
					},
					tooltip: {
						contentGenerator : function(input) { //key, x, y, e, graph
					
						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ input.data.key
						+ '</h4>'
						+ '<p>'
						+ input.data.y
						+ ' on '
						+ input.data.x
						+ '</p></div>'
						}
					},
					multibar : {
						/*dispatch : {
							elementClick : function(e) {
								$scope.clickedElement = e;
								handleElementClick(e);	
							}
						}*/
					},
					legend : {
	
					}
	
				},
				title : {
					enable : true,
					text : 'Google Analytics: Website Visitors'
				}
	
		};
		
		/*scope_options.google_analytics = {
				chart : {
					type : 'candlestickBarChart',
					x: function(d) { return d['date'] },
		            y: function(d) { return d['high'] },
					height : 450,
					margin : {
						top : 20,
						right : 20,
						bottom : 60,
						left : 45
					},
					xAxis: {
						axisLabel: "Dates"
					},
					yAxis: {
						axisLabel: "Visitors"
					},
					candlestick : {
					
					}
				}
		};*/
		
		scope_options.scope = $scope;
	
		return scope_options;
    } // end of getScopeOptions
    
    function natcmp(a, b) {
		var x = [], y = [];

		a['x'].replace(/(\d+)|(\D+)/g, function($0, $1, $2) {
			x.push([ $1 || 0, $2 ])
		})
		b['x'].replace(/(\d+)|(\D+)/g, function($0, $1, $2) {
			y.push([ $1 || 0, $2 ])
		})

		while (x.length && y.length) {
			var xx = x.shift();
			var yy = y.shift();
			var nn = (xx[0] - yy[0]) || strcmp(yy[1], xx[1]);
			if (nn)
				return nn;
		}

		if (x.length)
			return -1;
		if (y.length)
			return +1;

		return 0;
	} // end of natcmp
    
  }
})();