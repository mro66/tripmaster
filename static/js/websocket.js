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
			// mylog(message);
			// 1, 2,    3,   4        5,        6,         7,         8,                9,                      10 
			// T, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_TO_BE_DRIVEN, FRAC_SECTOR_DRIVEN
			KMH = values[3]; AVG_KMH = values[4]; KM_TOTAL = values[5]; KM_RALLYE = values[6]; KM_SECTOR = values[7];
			KM_SECTOR_PRESET = values[8]; KM_SECTOR_TO_BE_DRIVEN = values[9]; FRAC_SECTOR_DRIVEN = values[10];
			// Tacho
			if (document.getElementById("circulargauge-speed") !== null) {
				speedGauge = $('#circulargauge-speed').dxCircularGauge('instance');
				// Die aktuelle Geschwindigkeit ist der Hauptwert, ...
				speedGauge.value(KMH);
				// ... die Durchschnittsgeschwindigkeit der Nebenwert des Tachos 
				speedGauge.subvalues([AVG_KMH]);
				// Vorgegebene  Durchschnittsgeschwindigkeit TODO
				var AVG_KMH_PRESET = 90.0;
			} 
			// Odometer, mit , als Dezimaltrennzeichen
			if (document.getElementById("odometer-kmtotal") !== null) {
				document.getElementById("odometer-kmtotal").innerHTML = parseFloat(KM_RALLYE).toLocaleString('de-DE');
			} 
			if (document.getElementById("odometer-kmsector") !== null) {
				document.getElementById("odometer-kmsector").innerHTML = parseFloat(KM_SECTOR).toLocaleString('de-DE');
			// Linearanzeige: restliche km im Abschnitt
			} 
			if (document.getElementById("lineargauge-kmsector") !== null) {
				kmSectorPreset = KM_SECTOR_PRESET;
				kmLeftInSector = KM_SECTOR_TO_BE_DRIVEN;
				$("#lineargauge-kmsector").dxLinearGauge('instance').option("value", FRAC_SECTOR_DRIVEN);
				if (FRAC_SECTOR_DRIVEN > 0) { subvalues = [FRAC_SECTOR_DRIVEN]; } else { subvalues = []};
				$("#lineargauge-kmsector").dxLinearGauge('instance').option("subvalues", subvalues);
            } 
			// Entfernungstextboxen
			// Vorgabe des Abschnitts
			if (document.getElementById("textbox-sectorpreset") !== null) {
				$("#textbox-sectorpreset").dxTextBox('instance').option("value", formatDistance(KM_SECTOR_PRESET));
			} 
			// Abschnitt
			if (document.getElementById("textbox-sectorcounter") !== null) {
				$("#textbox-sectorcounter").dxTextBox('instance').option("value", formatDistance(KM_SECTOR));
			} 
			// Rallye
			if (document.getElementById("textbox-rallyecounter") !== null) {
				$("#textbox-rallyecounter").dxTextBox('instance').option("value", formatDistance(KM_RALLYE));
			} 
			// Gesamt
			if (document.getElementById("textbox-totalcounter") !== null) {
				$("#textbox-totalcounter").dxTextBox('instance').option("value", formatDistance(KM_TOTAL));
			} 
		} else {
			mylog('<-: '+message);
		
			TEXT = values[0];
			TYPE = values[1]; // ("info", "warning", "error" or "success")
			COMMAND = values[2];
			
			if (values.length == 3) {
				if ((COMMAND = "masterStarted") && (document.getElementById("switch-pausetripmaster") !== null)) {
					$("#switch-pausetripmaster").dxSwitch('instance').option("value", false);
				}
			};
			DevExpress.ui.notify(TEXT, TYPE);
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
