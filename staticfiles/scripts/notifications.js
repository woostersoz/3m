$(function() { 
	
	toastr.options = {
			  "closeButton": true,
			  "debug": false,
			  "positionClass": "toast-top-right",
			  "onclick": null,
			  "showDuration": "1000",
			  "hideDuration": "1000",
			  "timeOut": "5000",
			  "extendedTimeOut": "1000",
			  "showEasing": "swing",
			  "hideEasing": "linear",
			  "showMethod": "fadeIn",
			  "hideMethod": "fadeOut"
			}

    var socket = io.connect(
        ":8000/notifications",
        {
            "reconnectionDelay": 5000,
            "timeout": 10000,
            "resource": "socket.io",
           
        }
    );

    socket.on('connect', function(){
        console.log('connect', socket);
    });
    socket.on('notification', function(notification){ 
    	
        console.log('notification', notification);

        if (notification.type === "post_save") {
            if (notification.created) {
               toastr.success("Backtest \"" + notification.name + "\" has been run", "Backtest Success");
            } else {
                
            }
        } else if (notification.type === "post_delete") {
            var feature = map.data.getFeatureById(notification.feature.id);
            map.data.remove(feature);
        } else if (notification.type === "error") {
            toastr.error(notification.message)
        } else {
            console.log(notification);
        }
    });
    socket.on('disconnect', function(){
        console.log('disconnect', socket);
    });
});