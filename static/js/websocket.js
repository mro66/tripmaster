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
			if ((document.getElementById("odometer-kmsector") !== null)) {
                kmtotal.render();
                $("#odometer-kmtotal").ready(function() { 
                    kmsector.render();
                    $("#odometer-kmsector").ready(function() { 
                        resizeAndPosition();
                    });
                });
			};
		}
        if ((document.getElementById("lineargauge-kmsector") !== null)) {
			lineargauge = $("#lineargauge-kmsector").dxLinearGauge('instance');
            lineargauge.option("animation.duration", SAMPLE_TIME);
		}
        WebSocket_Send("getAllPoints");

        // DevExpress.ui.notify("WebSocket geöffnet", "success");
    }
    wss.onclose = function(evt) {
        if (isset(evt.reason)) {
        	mylog('Verbindung geschlossen:'+evt.reason);
        } else {
        	mylog('Verbindung geschlossen!');
        }
		DevExpress.ui.notify("WebSocket geschlossen", "warning");
        if ((document.getElementById("reloadpage") !== null)) {
			document.getElementById("reloadpage").style.display = "flex";
		}
        set_wss_status("closed");
    }
    wss.onmessage = function(evt) {
		var message = evt.data;
        var values = message.split(':');
        if (values[0] == "data") {
			mylog(message);
	// 1,     2,    3,   4        5,        6,        7,         8,                9,                     10,                 11,          12,       13,  14
	// INDEX, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_STAGE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, DEV_AVG_KMH, GPS_MODE, LAT, LON
	// 15,          16,           17,            18,             19
	// HAS_SENSORS, IS_TIME_SYNC, STAGE_STARTED, STAGE_FRACTIME, STAGE_RESTTIME
			INDEX = values[1]; KMH = values[3]; AVG_KMH = values[4]; KM_TOTAL = values[5]; KM_STAGE = values[6]; KM_SECTOR = values[7];
			KM_SECTOR_PRESET = values[8]; KM_SECTOR_PRESET_REST = values[9]; FRAC_SECTOR_DRIVEN = values[10]; DEV_AVG_KMH = values[11];
			GPS_MODE = parseInt(values[12]); 
            LAT = values[13]; LON = values[14]; HAS_SENSORS = values[15]; IS_TIME_SYNC = values[16];
            STAGE_STARTED = values[17], 
            STAGE_FRACTIME = parseInt(values[18]), 
            STAGE_RESTTIME = values[19].replace("&#058;", ":");

			// Tacho
			if (document.getElementById("circulargauge-speed") !== null) {
				let speedGauge = $('#circulargauge-speed').dxCircularGauge('instance');
				// Die aktuelle Geschwindigkeit ist der Hauptwert, ...
				speedGauge.value(KMH);
				// ... die Durchschnittsgeschwindigkeit der Nebenwert des Tachos
                if (STAGE_FRACTIME == 0) {
                    speedGauge.subvalues([AVG_KMH]);
                    speedGauge.option("subvalueIndicator", {"color": "gray"});
                } else {
                    speedGauge.subvalues([STAGE_FRACTIME]);
                    if (STAGE_FRACTIME < 80) {
                        fontColor = "var(--tm-green)";
                    } else if (STAGE_FRACTIME < 100) {
                        fontColor = "var(--tm-yellow)";
                    } else {
                        fontColor = "var(--tm-red)";
                    }
                    speedGauge.option("subvalueIndicator", {"color": fontColor});
                }
			} 
			// Odometer, mit , als Dezimaltrennzeichen
			if (document.getElementById("odometer-kmtotal") !== null) {
                // aus den 10m die 100m _nicht_ runden, sondern abschneiden
				KM_STAGE_TRUNC = Math.trunc(KM_STAGE * 10) / 10;
				document.getElementById("odometer-kmtotal").innerHTML = parseFloat(KM_STAGE_TRUNC).toLocaleString('de-DE');
			} 
			if (document.getElementById("odometer-kmsector") !== null) {
                let odometerKmSector = document.getElementById("odometer-kmsector");
                // Wenn Abschnittslänge eingestellt..
                // if (KM_SECTOR_PRESET > 0) {
                    // odometerKmSector.style.color = "var(--tm-red)";
                    // odometerKmSector.innerHTML = parseFloat(KM_SECTOR_PRESET_REST).toLocaleString('de-DE');
                // } else {
                    // odometerKmSector.style.color = "var(--tm-digit)";
                    odometerKmSector.innerHTML = parseFloat(KM_SECTOR).toLocaleString('de-DE');
                // };
			} 
			// Linearanzeige: restliche km im Abschnitt
			if (document.getElementById("lineargauge-kmsector") !== null) {
                lineargauge = $("#lineargauge-kmsector").dxLinearGauge('instance')
				kmSectorPreset = KM_SECTOR_PRESET;
                oldLeftInSector = kmLeftInSector;
				kmLeftInSector = KM_SECTOR_PRESET_REST;
                diffLeftInSector = kmLeftInSector - oldLeftInSector;
                // mylog("kmSectorPreset: " + kmSectorPreset);
                if (kmSectorPreset > 0) {
                    lineargauge.option("value", FRAC_SECTOR_DRIVEN);
                    lineargauge.option("subvalues", [FRAC_SECTOR_DRIVEN]);
                    // Letzter Eintrag vor Stopp
                    if ((kmLeftInSector == 0.0) && (diffLeftInSector != 0.0)) {
                        setTimeout(function() {
                            buttonsToFront();
                        }, 3000);                        
                    } 
                } ;
            } 
            // Statusanzeige: GPS
			if (document.getElementById("status-gps") !== null) {
				switch(GPS_MODE) {
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
            };
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
			};
            // Etappe starten und beenden
			if (document.getElementById("button-togglestage") !== null) {
                let togglestage = $("#button-togglestage").dxButton('instance');
                togglestage.option("disabled", (parseInt(IS_TIME_SYNC) == 0));
				if((parseInt(STAGE_STARTED) == 0)) {
                    if (isset(stageStarted)) stageStarted = false;
					togglestage.option("elementAttr", {"style": "color: var(--tm-red)"});
				} else {
                    if (isset(stageStarted)) stageStarted = true;
					togglestage.option("elementAttr", {"style": "color: var(--tm-green)"});
				};
                // if (document.getElementById("datebox-stageend") !== null) {
                    // let stageend = $("#datebox-stageend").dxDateBox('instance')
                    // if (!stageStarted) {
                        // stageend.reset();
                    // }
                    // stageend.option("disabled", !stageStarted);
                // };
			};
            // Kreisverkehre, Ortsschilder und OKs aktivieren
            let buttons = ["roundabout", "townsign", "checkpoint"];
            for (let button of buttons) {
                if (document.getElementById("button-"+button) !== null) {
                    let isDisabled = (parseInt(STAGE_STARTED) == 0)
                    $("#button-"+button).dxButton('instance').option("disabled", isDisabled);
                };
            };
            // Etappenrestzeit
			if (document.getElementById("textbox-timeinstage") !== null) {
				$("#textbox-timeinstage").dxTextBox('instance').option("value", STAGE_RESTTIME);
			};            
			// Entfernungstextboxen
			// Vorgegebene Abschnittslänge
			if (document.getElementById("textbox-sectorpreset") !== null) {
				$("#textbox-sectorpreset").dxTextBox('instance').option("value", formatDistance(KM_SECTOR_PRESET));
			};
			// Verbleibende Abschnittslänge
			if (document.getElementById("textbox-sectorpresetrest") !== null) {
				$("#textbox-sectorpresetrest").dxTextBox('instance').option("value", formatDistance(KM_SECTOR_PRESET_REST));
			};
			// Abschnitt
			if (document.getElementById("textbox-sector") !== null) {
				$("#textbox-sector").dxTextBox('instance').option("value", formatDistance(KM_SECTOR));
			};
			// Etappe
			if (document.getElementById("textbox-stage") !== null) {
				$("#textbox-stage").dxTextBox('instance').option("value", formatDistance(KM_STAGE));
			};
			// Gesamt
			if (document.getElementById("textbox-total") !== null) {
				$("#textbox-total").dxTextBox('instance').option("value", formatDistance(KM_TOTAL));
			} 
			// Abweichung der durchschnittlichen Geschwindigkeit von der Vorgabe
			if ((document.getElementById("circulargauge-devavgspeed") !== null)) {
				devAvgSpeed = $('#circulargauge-devavgspeed').dxCircularGauge('instance');
				devAvgSpeed.value(DEV_AVG_KMH);
				devAvgSpeed.subvalues([DEV_AVG_KMH]);
			} 
		} else if (values[0] == "countdown") {
			// mylog(message);
			var secondsleft = values[1]
			if (document.getElementById("textbox-regtesttime") !== null) {
				$("#textbox-regtesttime").dxTextBox('instance').option("value", secondsleft + " sek");
			}
            if (secondsleft > 0) {
                if (document.getElementById("textbox-regtestlength") !== null) {
                    $("#textbox-regtestlength").dxTextBox('instance').option("value", formatDistance(KM_SECTOR_PRESET_REST));
                }
                if (document.getElementById("textbox-regtestavgspeed") !== null) {
                    let speedDeviation = formatSpeed(DEV_AVG_KMH);
                    if (DEV_AVG_KMH > 0) speedDeviation = "+" + speedDeviation;
                    $('#textbox-regtestavgspeed').dxTextBox('instance').option("value", speedDeviation);
                } 
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
            TEXT = TEXT.replace("&#058;", ":");
			TYPE = values[1]; // ("info", "warning", "error" or "success")
			COMMAND = values[2];
			
			if (values.length == 3) {
                if (COMMAND == "sectorReset") {
                    if (document.getElementById("lineargauge-kmsector") !== null) {
                        lineargauge = $("#lineargauge-kmsector").dxLinearGauge('instance')
                        lineargauge.option("value", 0);
                        lineargauge.option("subvalues", []);
                    };
                } else if (COMMAND.startsWith("countpointRegistered") || COMMAND.startsWith("checkpointRegistered")) {
                    pointtype = COMMAND.split("#")[0].replace("Registered", "");
                    if (document.getElementById("datagrid-" + pointtype) !== null) {
                        pointdata = COMMAND.split('#');
                        pointDataGrid = $("#datagrid-" + pointtype).dxDataGrid("instance");
                        pointDataGrid.getDataSource().store().insert(
                            {
                                ID: parseInt(pointdata[1]),
                                Beschreibung: pointdata[2],
                                Name: pointdata[3],
                                Sicher: pointdata[4] == 1?true:false,
                            })
                        .done(function (dataObj, key) { /* Process the key and data object here*/ })
                        .fail(function (error) {/* Handle the "error" here */});
                        pointDataGrid.refresh();
                    };
                };
                // Nur Dashboard
				if (document.getElementById("multiview-dashboard") !== null) {
					if (COMMAND == "regTestStarted") {
						$("#multiview-dashboard").dxMultiView('instance').option("selectedIndex", 1);
					} else if (COMMAND == "regTestStopped") {
						setTimeout(function() {
                            $("#multiview-dashboard").dxMultiView('instance').option("selectedIndex", 0);
                            AVG_KMH_PRESET = 0;
                            $('#circulargauge-devavgspeed').dxCircularGauge('instance').option("scale.label.customizeText", function(arg) {
                                return formatSpeed(AVG_KMH_PRESET);
                            });
                        }, 2000);
					} else if (COMMAND == "sectorReset") {
                        setTimeout(function() {
                            buttonsToFront();
                        }, 2000);                        
					} else if (COMMAND == "sectorLengthset") {
                        if (document.getElementById("button-group") !== null) {
                            linearGaugeToFront();
                        };
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
