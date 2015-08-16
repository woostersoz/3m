(function () {
  'use strict';

  angular
    .module('mmm.filters', [])
    .filter('backtestStatus', function() {
    	return function(input) {
    		var status = {
    	    		'0': function() { 
    	    			return '\u2423';
    	    		},
    	    		'1': function() {
    	    			return '\u2713';
    	    		},
    	    		'2': function() {
    	    			return '\u2718';
    	    		},
    		 };
    		 if (typeof status[input] !== 'function') {
    			return '?';
    		 }		
	         return status[input]();
    	}
    })
    .filter('dataHandler', function() {
    	return function(input) {
    		var dh = {
    	    		'HistoricCSVDataHandler': function() { 
    	    			return 'Historic CSV';
    	    		},
    	    		'1': function() {
    	    			return '\u2713';
    	    		},
    	    		'2': function() {
    	    			return '\u2718';
    	    		},
    		 };
    		 if (typeof dh[input] !== 'function') {
    			return '?';
    		 }		
	         return dh[input]();
    	}
    })
    .filter('executionHandler', function() {
    	return function(input) {
    		var eh = {
    	    		'SimulatedExecutionHandler': function() { 
    	    			return 'Simulated Execution';
    	    		},
    	    		'1': function() {
    	    			return '\u2713';
    	    		},
    	    		'2': function() {
    	    			return '\u2718';
    	    		},
    		 };
    		 if (typeof eh[input] !== 'function') {
    			return '?';
    		 }		
	         return eh[input]();
    	}
    })
    .filter('portfolio', function() {
    	return function(input) {
    		var portfolio = {
    	    		'EqualWeightedPortfolio': function() { 
    	    			return 'Equal Weighted';
    	    		},
    	    		'1': function() {
    	    			return '\u2713';
    	    		},
    	    		'2': function() {
    	    			return '\u2718';
    	    		},
    		 };
    		 if (typeof portfolio[input] !== 'function') {
    			return '?';
    		 }		
	         return portfolio[input]();
    	}
    })
    .filter('strategy', function() {
    	return function(input) {
    		var strategy = {
    	    		'MovingAverageCrossStrategy': function() { 
    	    			return 'Moving Average Cross';
    	    		},
    	    		'1': function() {
    	    			return '\u2713';
    	    		},
    	    		'2': function() {
    	    			return '\u2718';
    	    		},
    		 };
    		 if (typeof strategy[input] !== 'function') {
    			return '?';
    		 }		
	         return strategy[input]();
    	}
    });


})();