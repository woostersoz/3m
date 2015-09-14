// Inject jQuery
console.log('in PJS script');
//phantom.injectJs("../static/jquery.js");
var page, system, fs, info, csrftoken, sessionid, authenticatedAccount, address, output;
// Create a page object
page = require('webpage').create();
page.onConsoleMessage = function(msg) {
	console.log('PhantomJS message: ' + msg);
}
// Require the system module so I can read the command line arguments
system = require('system');
// Require the FileSystem module, so I can read the cookie file
fs = require('fs');
console.log('done with fs');
// Read the url and output file location from the command line argument
address = system.args[1];
output = system.args[5];
csrftoken = system.args[2];
sessionid = system.args[3];
authenticatedAccount = system.args[4];
//htmlarray = system.args[5]
console.log('done with urlparams')
// set cookie values for authentication
phantom.addCookie({domain: 'app.claritix.io', 'name': 'csrftoken', 'value': csrftoken})
phantom.addCookie({domain: 'app.claritix.io', 'name': 'sessionid', 'value': sessionid})
phantom.addCookie({domain: 'app.claritix.io', 'name': 'authenticatedAccount', 'value': authenticatedAccount})
console.log('done with cookie');
// Set the page size and orientation
page.paperSize = {
    format: 'A4',
    orientation: 'landscape'};
// Now we have everything settled, let's render the page
console.log('address is ' + address);

/*page.onError = function(msg, trace) {
	var msgStack = ['ERROR: ' + msg];
	
	if (trace && trace.length) {
		msgStack.push('TRACE:');
		trace.forEach(function(t) {
			msgStack.push(' -> ' + t.file + ': ' + t.line + (t.function ? ' (in function "' + t.function +'")' : ''));
	    });
	}
	console.error(msgStack.join('\n'));
}

phantom.onError = function(msg, trace) {
	  var msgStack = ['PHANTOM ERROR: ' + msg];
	  if (trace && trace.length) {
	    msgStack.push('TRACE:');
	    trace.forEach(function(t) {
	      msgStack.push(' -> ' + (t.file || t.sourceURL) + ': ' + t.line + (t.function ? ' (in function ' + t.function +')' : ''));
	    });
	  }
	  console.error(msgStack.join('\n'));
	  phantom.exit(1);
};
*/

page.onInitialized = function() {
	page.evaluate(function() {
	      document.addEventListener('_htmlReady', function() {
	    	console.log('event happened');
	        window.callPhantom();
	      }, false);
	});
};

page.onCallback = function() {
    console.log('from cb on ');
    setTimeout(function() { console.log('in timeout');
      page.render(output);
      page.close();
      phantom.exit();
    }, 5000);
    
};


page.open(address, function (status) { console.log('status ' + status);
    if (status !== 'success') {
        // If PhantomJS failed to reach the address, print a message
        console.log('Unable to load the address!');
        phantom.exit();
    } else {
        // If we are here, it means we rendered page successfully
        // Use "evaluate" method of page object to manipulate the web page
        // Notice I am passing the data into the function, so I can use
        // them on the page

        // Now create the output file and exit PhantomJS
        
    }
});