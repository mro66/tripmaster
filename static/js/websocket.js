// WebSocket
var wss;
var wss_status = "closed";

function set_wss_status(status) {
    wss_status = status;
    if (document.getElementById("connectionStatus") !== null) {
        document.getElementById("connectionStatus").innerHTML = status;
    }
}

function WebSocket_Close() {
    wss.close();
}

function WebSocket_Open(page) {
    wss = new WebSocket("wss://"+location.hostname+":7070/"+page);
    wss.onerror = function(evt) {
        mylog('Fehler: '+evt.data);
    }
    wss.onopen = function() {
        mylog('Verbindung geöffnet!');
        set_wss_status("opened");
        if (document.getElementById("circulargauge-speed") !== null) {
			$('#circulargauge-speed').dxCircularGauge('instance').option("animation.duration", SAMPLE_TIME);
		}
        if ((document.getElementById("lineargauge-kmsector") !== null)) {
			$("#lineargauge-kmsector").dxLinearGauge('instance').option("animation.duration", SAMPLE_TIME);
			if ((document.getElementById("odometer-kmsector") !== null)) {
				resizeAndPosition();
			}
		}
		DevExpress.ui.notify("WebSocket geöffnet", "success");
    }
    wss.onclose = function(evt) {
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
        set_wss_status("closed");
    }
    wss.onmessage = function(evt) {
		var message = evt.data;
        var values = message.split(':');
        if (values[0] == "data") {
			mylog(message);
	// 1,     2,    3,   4        5,        6,         7,         8,                9,                      10,                 11,          12,       13,  14
	// INDEX, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_TO_BE_DRIVEN, FRAC_SECTOR_DRIVEN, DEV_AVG_KMH, GPS_MODE, LAT, LON
	// 15
	// HAS_SENSORS
			KMH = values[3]; AVG_KMH = values[4]; KM_TOTAL = values[5]; KM_RALLYE = values[6]; KM_SECTOR = values[7];
			KM_SECTOR_PRESET = values[8]; KM_SECTOR_TO_BE_DRIVEN = values[9]; FRAC_SECTOR_DRIVEN = values[10]; DEV_AVG_KMH = values[11];
			GPS_MODE = values[12]; LAT = values[13]; LON = values[14]; HAS_SENSORS = values[15];
			// Tacho
			if (document.getElementById("circulargauge-speed") !== null) {
				speedGauge = $('#circulargauge-speed').dxCircularGauge('instance');
				// Die aktuelle Geschwindigkeit ist der Hauptwert, ...
				speedGauge.value(KMH);
				// ... die Durchschnittsgeschwindigkeit der Nebenwert des Tachos 
				speedGauge.subvalues([AVG_KMH]);
			} 
			// Odometer, mit , als Dezimaltrennzeichen
			if (document.getElementById("odometer-kmtotal") !== null) {
				KM_RALLYE_TRUNC = Math.trunc(KM_RALLYE * 10) / 10;
				document.getElementById("odometer-kmtotal").innerHTML = parseFloat(KM_RALLYE_TRUNC).toLocaleString('de-DE');
			} 
			if (document.getElementById("odometer-kmsector") !== null) {
				document.getElementById("odometer-kmsector").innerHTML = parseFloat(KM_SECTOR).toLocaleString('de-DE');
			} 
			// Linearanzeige: restliche km in der Etappe
			if (document.getElementById("lineargauge-kmsector") !== null) {
				kmSectorPreset = KM_SECTOR_PRESET;
				kmLeftInSector = KM_SECTOR_TO_BE_DRIVEN;
				$("#lineargauge-kmsector").dxLinearGauge('instance').option("value", FRAC_SECTOR_DRIVEN);
				if (FRAC_SECTOR_DRIVEN > 0) { subvalues = [FRAC_SECTOR_DRIVEN]; } else { subvalues = []};
				$("#lineargauge-kmsector").dxLinearGauge('instance').option("subvalues", subvalues);
            } 
            // Statusanzeige: GPS
			if (document.getElementById("status-gps") !== null) {
				switch(parseInt(GPS_MODE)) {
					case 0:
						fontColor = "lightgray";
						break;
					case 1:
						fontColor = "var(--tm-red)";
						break;
					case 2:
						fontColor = "var(--tm-yellow)";
						break;
					case 3:
						fontColor = "var(--tm-green)";
						break;
					default:
						fontColor = "Ivory";
				};
                document.getElementById("status-gps").style.color = fontColor;
            }
            // Statusanzeige: Radsensor
			if (document.getElementById("status-tyre") !== null) {

				switch(parseInt(HAS_SENSORS)) {
					case 0:
						fontColor = "lightgray";
						break;
					case 1:
						fontColor = "var(--tm-green)";
						break;
					default:
						fontColor = "Ivory";
				};
                document.getElementById("status-tyre").style.color = fontColor;
			}
			// Entfernungstextboxen
			// Vorgegebene Etappenlänge
			if (document.getElementById("textbox-sectorpreset") !== null) {
				$("#textbox-sectorpreset").dxTextBox('instance').option("value", formatDistance(KM_SECTOR_PRESET));
			} 
			// Etappe
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
			// Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
			if ((document.getElementById("circulargauge-devavgspeed") !== null)) {
				devAvgSpeed = $('#circulargauge-devavgspeed').dxCircularGauge('instance');
				devAvgSpeed.value(DEV_AVG_KMH);
				devAvgSpeed.subvalues([DEV_AVG_KMH]);
			} 
		} else if (values[0] == "is_started") {
			// mylog(message);
			// TODO: Tripmaster komplett starten/stoppen
		} else if (values[0] == "is_recording") {
			// mylog(message);
			var recpaused = values[1]==0?true:false;
			if (document.getElementById("switch-stoptripmaster") !== null) {
				$("#switch-stoptripmaster").dxSwitch('instance').option("value", recpaused);
			};
			if (document.getElementById("status-information") !== null) {
				if(recpaused) {
					$("#button-togglerecording").dxButton('instance').option("icon", "fas fa-circle");
					$("#button-togglerecording").dxButton('instance').option("elementAttr", {"style": "color: var(--tm-red)"});
				} else {
					$("#button-togglerecording").dxButton('instance').option("icon", "fas fa-pause-circle");
					$("#button-togglerecording").dxButton('instance').option("elementAttr", {"style": "color: var(--tm-yellow)"});
				}
			};
			// Tacho
			if (recpaused && document.getElementById("circulargauge-speed") !== null) {
				$('#circulargauge-speed').dxCircularGauge('instance').value(0);
			};
		} else if (values[0] == "countdown") {
			// mylog(message);
			var countdown = values[1]
			if (document.getElementById("textbox-regtestseconds") !== null) {
				$("#textbox-regtestseconds").dxTextBox('instance').option("value", countdown + " sek");
			}
		} else if (values[0] == "avgspeed") {
			// mylog(message);
			if (document.getElementById("circulargauge-devavgspeed") !== null) {
				AVG_KMH_PRESET = parseFloat(values[1]);
				$('#circulargauge-devavgspeed').dxCircularGauge('instance').option("scale.label.customizeText", function(arg) {return formatSpeed(AVG_KMH_PRESET);});
			} 
		} else if (values[0] == "getConfig") {
			// mylog(message);
			var keyvalues = values[1].split('&');
			if (document.getElementById("popup-editconfiguration") !== null) {
				for (var i=0; i<keyvalues.length; i++) {
					keyvalue = keyvalues[i].split('=');
					document.getElementById("label-key"+i).innerHTML = keyvalue[0];
					$("#textbox-key"+i).dxTextBox('instance').option("value", keyvalue[1]);
				};
			} 
		} else {
			// mylog('<-: '+message);
		
			TEXT = values[0];
			TYPE = values[1]; // ("info", "warning", "error" or "success")
			COMMAND = values[2];
			
			if (values.length == 3) {
				if (document.getElementById("multiview-dashboard") !== null) {
					if (COMMAND == "regTestStarted") {
						$("#multiview-dashboard").dxMultiView('instance').option("selectedIndex", 1);
					} else if (COMMAND == "regTestStopped") {
						setTimeout(function() 
							{
								$("#multiview-dashboard").dxMultiView('instance').option("selectedIndex", 0);
								AVG_KMH_PRESET = 0;
								$('#circulargauge-devavgspeed').dxCircularGauge('instance').option("scale.label.customizeText", function(arg) {
									return formatSpeed(AVG_KMH_PRESET);
								});
							}, 2000);
					}
				};
			};
			DevExpress.ui.notify(TEXT, TYPE);
		}
    }
}

function WebSocket_Send(data) {
    if (wss_status == "opened") {
        wss.send(data);
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
