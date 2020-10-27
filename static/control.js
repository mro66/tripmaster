if (typeof(String.prototype.strip) === "undefined") {
    String.prototype.strip = function() {
        return String(this).replace(/^\s+|\s+$/g, '');
    };
}

function isset(strVariableName) { 
    try { 
        eval( strVariableName );
    } catch( err ) { 
        if ( err instanceof ReferenceError ) 
            return false;
    }
    return true;
}

function sleep(millis, callback) {
    setTimeout(function() { callback(); } , millis);
}

//source of: http://www.html5tutorial.info/html5-range.php
function printValue(sliderID, textbox) {
    var x = document.getElementById(textbox);
    var y = document.getElementById(sliderID);
    x.value = y.value;
}


function mylog(message) {
    if (isset(DEBUG) && DEBUG == 1) {
        console.log(message);
        if (document.getElementById("Log") !== null) {
            var logthingy;
            logthingy = document.getElementById("Log");
            if( logthingy.innerHTML.length > 5000 )
                logthingy.innerHTML = logthingy.innerHTML.slice(logthingy.innerHTML.length-5000);
            logthingy.innerHTML = /*logthingy.innerHTML+"<br/>"+*/message;
            logthingy.scrollTop = logthingy.scrollHeight*2;
        }
    }
}

//----------------------------------------------------------------

/*
var telemetryTimer;
$(document).ready(function() {
    // start Main Timers
    telemetryTimer = setTimeout(get_telemetry, 1000);
});
*/

function Send(command) {
    $.ajax({
        type: "GET",
        url: "/cmd/" + command,
        dataType: "JSON",
        success: function(data) {
            mylog("Command Response: " + data);
            if (document.getElementById(command) !== null) {
                document.getElementById(command).innerHTML = data;
            }
        }
    });
}

function get_telemetry() {
    $.getJSON("/data/")
    .fail(function() {
        console.log("Error processing get_telemetry");
        clearTimeout(telemetryTimer);
    })
    .done(function(data) {
        $.each(data, function(id,val) {
            if (document.getElementById(id) !== null) {
                mylog("JSON Data: " + id + ":" + val);

                if (id == "LoadAVGnum") {
                    document.getElementById(id).innerHTML = val + "%";
                } else if (id == "LoadAVGperc") {
                    document.getElementById(id).value = val;
                } else if (id == "RAMnum") {
                    document.getElementById(id).innerHTML = val + "MB";
                } else if (id == "RAMperc") {
                    document.getElementById(id).value = val;

                } else {
                    document.getElementById(id).innerHTML = val;
                }
            }
        })
        telemetryTimer = setTimeout(get_telemetry, 2000);
    });
}