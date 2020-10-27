var ws;
var ws_status = "closed";
function set_ws_status(status) {
    ws_status = status;
    if (document.getElementById("connectionStatus") !== null) {
        document.getElementById("connectionStatus").innerHTML = status;
    }
}

function WebSocket_Close() {
    ws.close();
}

function WebSocket_Open(page) {
    ws = new WebSocket("ws://"+location.hostname+":7070/"+page);
    ws.onerror = function(evt) {
        mylog('Fehler: '+evt.data);
    }
    ws.onopen = function() {
        mylog('Verbindung geöffnet!');
        set_ws_status("opened");
        if (document.getElementById("circulargauge-speed") !== null) {
			$('#circulargauge-speed').dxCircularGauge('instance').option("animation.duration", SAMPLE_TIME);
		}
        if ((document.getElementById("lineargauge-kmsector") !== null)) {
			$("#lineargauge-kmsector").dxLinearGauge('instance').option("animation.duration", SAMPLE_TIME);
		}
		DevExpress.ui.notify("WebSocket geöffnet", "success");
    }
    ws.onclose = function(evt) {
        if (isset(evt.reason)) {
        	mylog('Verbindung geschlossen:'+evt.reason);
        } else {
        	mylog('Verbindung geschlossen!');
        }
		DevExpress.ui.notify("WebSocket geschlossen", "warning");
        if ((document.getElementsByClassName("main") !== null)) {
			document.getElementsByClassName("main")[0].style.display = "none";
			$("#button-reloadpage").dxButton('instance').option("visible", true);
		}
        set_ws_status("closed");
    }
    ws.onmessage = function(evt) {
		var message = evt.data;
        var values = message.split(':');
        mylog('Empfangene Nachricht: >'+message+'<');
        if (values[0] == "data") { 
			if (document.getElementById("dashboard") !== null) {
				
				// Tacho
				speedGauge = $('#circulargauge-speed').dxCircularGauge('instance');
				// Die aktuelle Geschwindigkeit ist der Hauptwert, ...
				speedGauge.value(values[3]);
				// ... die Durchschnittsgeschwindigkeit der Nebenwert des Tachos 
				speedGauge.subvalues([values[4]]);
				
				// Vorgegebene  Durchschnittsgeschwindigkeit TODO
				var AVG_KMH_PRESET = 90.0;
				
				// Odometer
				document.getElementById("km_total").innerHTML = values[5];
				document.getElementById("km_sector").innerHTML = values[6];

				// Linearanzeige
				kmSectorPreset = values[7];
				kmSectorToBeDriven = values[8];
				setKmSector(values[9]);
			} else if (document.getElementById("settings") !== null) {
				// Linearanzeige
				kmSectorPreset = values[7];
				kmSectorToBeDriven = values[8];
				setKmSector(values[9]);
			} else {
				DevExpress.ui.notify("Weder Dashboard noch Settings gefunden!", "error");
			}
		} else {
			// values[0] = text, values[1] = type ("info", "warning", "error" or "success"), 
			DevExpress.ui.notify(values[0], values[1]);
		}
    }
}

function WebSocket_Send(data) {
    if (ws_status == "opened") {
        ws.send(data);
        mylog('Gesendete Nachricht: >>>'+data+'<<<');
    }
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

function mylog(message) {
    if (isset(DEBUG) && DEBUG == 1) {
        console.log(message);
        if (document.getElementById("Log") !== null) {
            var logthingy;
            logthingy = document.getElementById("Log");
            if( logthingy.innerHTML.length > 5000 )
                logthingy.innerHTML = logthingy.innerHTML.slice(logthingy.innerHTML.length-5000);
            logthingy.innerHTML = logthingy.innerHTML+"<br/>"+message;
            logthingy.scrollTop = logthingy.scrollHeight*2;
        }
    }
}
