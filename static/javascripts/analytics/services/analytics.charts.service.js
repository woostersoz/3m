/**
* Charts
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
      strcmp: strcmp,
      natcmp: natcmp,
      getScopeOptions: getScopeOptions      
    };

    return AnalyticsCharts;
    
    function strcmp(a, b) {
		return a > b ? -1 : a < b ? 1 : 0;
	}

    function natcmp(a, b) {
		var x = [];
		var y = [];

		a['x'].replace(/(\d+)|(\D+)/g, function(m, n, o) {
			x.push([ n || 0, o ]);
		});
		b['x'].replace(/(\d+)|(\D+)/g, function(m, n, o) {
			y.push([ n || 0, o ]);
		});

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
    
    function getScopeOptions(scope) {
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
						+ '</p></div>';
						}
					},
					multibar : {
						
					},
					legend : {
	
					}
	
				},
				title : {
					enable : false,
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
	                    axisLabel: ''
	                    
						
	                },
	                yAxis : {
						
	                	tickFormat : function(d) {
							return d3.format(',f')(d);
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
						+ '</p></div>';
					},
					multibar : {
					
					},
					legend : {
	
					}
	            },
				title : {
					enable : false,
					text : 'Contacts Distribution by Stage Date'
				}
	        };
		
			var numbers_to_labels = ['Subscribers', 'Leads', 'MQLs', 'SQLs', 'Opportunities', 'Customers', "All"];
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
					enable : false,
					text : 'Pipeline Duration by Stage Date'
				}
	  
	        };
		
//		var numbers_to_labels = ['Subscribers', 'Leads', 'MQLs', 'SQLs', 'Opportunities', 'Customers', "All"];
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
	                    	return scope.statuses[d];
	                    },
	                    showMaxMin: true,
	                    //width: 500
	                },
	                yAxis: {
	                	tickFormat: function(d) {
	                    	return scope.statuses[d];
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
						+ '</p></div>';
					},
					scatter : {
						onlyCircles: true,
						useVoronoi: false,
						clipVoronoi: false
						
					},
					legend : {
	
					}
	            },
				title : {
					enable : false,
					text : 'Pipeline Duration by Stage Date'
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
						+ '</p></div>';
						}
					},
					pie : {
					
						labelType: 'percent'
					},
					growOnHover: true,
					tooltips: true
	            },
				title : {
					enable : false,
					text : 'Revenue by Source Channel'
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
						+ '</p></div>';
						}
					},
					pie : {

						labelType: 'percent'
					},
					growOnHover: true,
					tooltips: true,
				
	            },
				title : {
					enable : false,
					text : 'Leads by Source based on Creation Date'
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
						+ '</p></div>';
						}
					},
					multibar : {
						
					},
					legend : {
	
					}
	
				},
				title : {
					enable : false,
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
						+ '</p></div>';
						}
					},
					multibar : {
						
					},
					legend : {
	
					}
	
				},
				title : {
					enable : false,
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
						+ '</p></div>';
						}
					},
					multibar : {
						
					},
					legend : {
	
					}
	
				},
				title : {
					enable : false,
					text : 'Google Analytics: Website Visitors'
				}
	
		};
		
		scope_options.facebook_organic_engagement = {
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
						axisLabel : 'Numbers',
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
						+ '</p></div>';
						}
					},
					multibar : {
						
					},
					legend : {
	
					}
	
				},
				title : {
					enable : false,
					text : 'Facebook Organic Engagement'
				}
	
		};
		
		scope_options.facebook_paid_engagement = {
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
						axisLabel : 'Numbers',
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
						+ '</p></div>';
						}
					},
					multibar : {
						
					},
					legend : {
	
					}
	
				},
				title : {
					enable : false,
					text : 'Facebook Paid Engagement'
				}
	
		};
		
		
		scope_options.scope = scope;
	
		return scope_options;
    } // end of getScopeOptions
    
    
    
  }
})();