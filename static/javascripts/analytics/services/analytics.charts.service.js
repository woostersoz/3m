/**
* Charts
* @namespace mmm.analytics.services
*/
(function () {
  'use strict';

  angular
    .module('mmm.analytics.services')
    .factory('AnalyticsCharts', AnalyticsCharts);

  AnalyticsCharts.$inject = ['$http', '$filter'];

  /**
  * @namespace AnalyticsCharts
  * @returns {Factory}
  */
  function AnalyticsCharts($http, $filter) {
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
		
		scope_options.google_pages = scope_options.google_analytics;
		scope_options.google_pages['chart']['yAxis']['axisLabel'] = 'Pages'; 
		scope_options.google_pages['chart']['showLegend'] = false;
		
		scope_options.google_sources = scope_options.google_analytics;
		scope_options.google_sources['chart']['yAxis']['axisLabel'] = 'Sources'; 
		scope_options.google_sources['chart']['showLegend'] = true;
		
		scope_options.google_os = scope_options.google_analytics;
		scope_options.google_os['chart']['yAxis']['axisLabel'] = 'Sources'; 
		scope_options.google_os['chart']['showLegend'] = true;
		
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
					type : 'multiBarHorizontalChart',
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
		
		scope_options.campaign_email_performance = {
	            chart: {
	                type: 'multiBarHorizontalChart',
	                height: 1200, //function(d) {return ((d.values.length * 20) + 'px')},
	                margin : {
	                    top: 20,
	                    right: 20,
	                    bottom: 60,
	                    left: 200
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
						},
						tickValues: [0, 1, 2, 3, 4]
	                
					},
	                tooltip :  { //function(key, x, y, e, graph)
/*						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ key
						+ '</h4>'
						+ '<p>'
						+ y
						+ ' on '
						+ x
						+ '</p></div>';*/
	                	contentGenerator : function(input) { //key, x, y, e, graph
							return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
							+ input.data.key
							+ '</h4>'
							+ '<p>'
							+ input.data.value
							+ ' on '
							+ input.data.label
							+ '</p></div>';
	                	}
					},
					multibar : {
					
					},
					legend : {
	
					}
	            },
	        };
		
		/*scope_options.campaign_email_performance = scope_options.horizontal_multibar;
		scope_options.campaign_email_performance['chart']['margin']['left'] = 200;
		scope_options.campaign_email_performance['chart']['height'] = 1200;*/
		
		/*scope_options.email_cta_performance = scope_options.horizontal_multibar;
		scope_options.email_cta_performance['chart']['margin']['left'] = 20;
		scope_options.email_cta_performance['chart']['xAxis']['orient'] = 'right';
		scope_options.email_cta_performance['chart']['yAxis']['tickValues'] = [0, 1, 2, 3, 4];
		scope_options.email_cta_performance['chart']['yAxis']['ticks'] = 5;
		scope_options.email_cta_performance['chart']['height'] = 1500;
		scope_options.email_cta_performance['chart']['x'] = function(d){return d.label.substring(0,99);}*/
		//scope_options.campaign_email_performance['chart']['yAxis']['orient'] = 'top';
		
		scope_options.email_cta_performance = {
	            chart: {
	                type: 'multiBarHorizontalChart',
	                height: 1500, //function(d) {return ((d.values.length * 20) + 'px')},
	                margin : {
	                    top: 20,
	                    right: 20,
	                    bottom: 60,
	                    left: 100
	                },
	                x: function(d){return $filter('unsafe')(d.label);}, //function(d){return d.label;},
	                y: function(d){return d.value;},
	                showValues: false,
	                showLegend: true,
	                showControls: true,
	                valueFormat: function(d){
	                    return d3.format(',f')(d);
	                },
	                transitionDuration: 500,
	                xAxis: {
	                	domain: scope.data.map(function(d) { return d.value; }),
	                	tickFormat: function(d, i) {
		                    d3.select(this.parentNode).append('a')
		                      .attr('xlink:href', function(d) { return scope.data[0]['values'][i].url; })
		                      .attr('xlink:show', 'new')
		                      .append('image')
		                      .attr('xlink:href', d) //
		                      .attr('x', -75).attr('y', -25)
		                      .attr('width', 50).attr('height', 50)
		                      .attr('class', 'svg-thumbnail')
		                      /*.on('mouseenter', function() { console.log('xxx');
		                    	  svg.selectAll('image').sort(function(a, b) {
		                    		  if (a.id != d.id) return -1;
		                    		  else return 1;
		                    	  });
		                      }); */
	                	},
	                	height: 150,
	                },
	                yAxis : {
						
	                	tickFormat : function(d) {
							return d3.format(',f')(d);
						},
						//tickValues: [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100],
						height: 150,
	                
					},
	                tooltip :  { //function(key, x, y, e, graph)
/*						return '<div style=\'text-align:center\'><h4 style=\'font-size:0.8rem !important\'>'
						+ key
						+ '</h4>'
						+ '<p>'
						+ y
						+ ' on '
						+ x
						+ '</p></div>';*/
	                	contentGenerator : function(input) { //key, x, y, e, graph
							return '<div style=\'text-align:center; width:500px;height:100%;white-space:normal;overflow:auto\'><h4 style=\'font-size:0.8rem !important\'>'
							+ input.data.key
							+ '</h4>'
							+ '<p style=\'text-align:left;height:100%;word-wrap;break-word;\'>'
							+ input.data.value
							+ ' on '
							+ input.data.url
							+ '</p></div>';
	                	}
					},
					multibar : {
					
					},
					legend : {
	
					}
	            },
	        };
		
		scope_options.scope = scope;
	
		return scope_options;
    } // end of getScopeOptions
    
    
    
  }
})();