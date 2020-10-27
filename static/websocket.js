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
			if ((document.getElementById("box-twocolumn") !== null)) {
				resizeAndPosition();
			}
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
        if (values[0] == "data") { 
			// T, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_TO_BE_DRIVEN, FRAC_SECTOR_DRIVEN

			// mylog('<- '+message);
			// Tacho
			if (document.getElementById("circulargauge-speed") !== null) {
				speedGauge = $('#circulargauge-speed').dxCircularGauge('instance');
				// Die aktuelle Geschwindigkeit ist der Hauptwert, ...
				speedGauge.value(values[3]);
				// ... die Durchschnittsgeschwindigkeit der Nebenwert des Tachos 
				speedGauge.subvalues([values[4]]);
				// Vorgegebene  Durchschnittsgeschwindigkeit TODO
				var AVG_KMH_PRESET = 90.0;
			} 
			// Odometer, mit , als Dezimaltrennzeichen
			if (document.getElementById("odometer-kmtotal") !== null) {
				document.getElementById("odometer-kmtotal").innerHTML = parseFloat(values[5]).toLocaleString('de-DE');
			} 
			if (document.getElementById("odometer-kmsector") !== null) {
				document.getElementById("odometer-kmsector").innerHTML = parseFloat(values[6]).toLocaleString('de-DE');
			// Linearanzeige: restliche km in der Etappe
			} 
			if (document.getElementById("lineargauge-kmsector") !== null) {
				kmSectorPreset = values[7];
				kmLeftInSector = values[8];
				setKmSector(values[9]);
			} 
			// Textboxen
			// Länge der Etappe
			if (document.getElementById("textbox-sectorpreset") !== null) {
				$("#textbox-sectorpreset").dxTextBox('instance').option("value", formatDistance(values[7]));
			} 
			// Strecke seit Reset
			if (document.getElementById("textbox-sector") !== null) {
				$("#textbox-sector").dxTextBox('instance').option("value", formatDistance(values[6]));
			} 
		} else {
			mylog('<-: '+message);
			// values[0] = text
			// values[1] = type ("info", "warning", "error" or "success")
			// values[2] = command
			// values[3] = parameter
			// values[4] = value
			if (values.length == 3) {
				if (document.getElementById("radio-group-pausetripmaster") !== null) {
					if (values[2] === "masterStart") {
						$("#radio-group-pausetripmaster").dxRadioGroup('instance').option("value", yesno[1]);
					} else if (values[2] === "masterPause") {
						$("#radio-group-pausetripmaster").dxRadioGroup('instance').option("value", yesno[0]);
					}
				}
			} else if (values.length == 5) {
				if (document.getElementById("numberbox-tyre-size") !== null) {
					$("#numberbox-tyre-size").dxNumberBox('instance').opion("value", parseFloat(values[4]));
				}
			};
			DevExpress.ui.notify(values[0], values[1]);
		}
    }
}

function WebSocket_Send(data) {
    if (ws_status == "opened") {
        ws.send(data);
        mylog('->: '+data);
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
