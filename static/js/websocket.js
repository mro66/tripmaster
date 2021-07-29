// WebSocket
var wss;
var wss_status = "closed";
var LASTUBAT_CAP = 0


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
    
    // Identifikation der Seite	
    dashboard = (page === "dashboard")
    settings  = (page === "settings")
    
    wss.onerror = function(evt) {
        mylog('Fehler: '+evt.data);
    }
    wss.onopen = function() {
        mylog('Verbindung geöffnet!');
        set_wss_status("opened");
        if (document.getElementById("circulargauge-speed") !== null) {
            $('#circulargauge-speed').dxCircularGauge("instance").option("animation.duration", SAMPLE_TIME);
            if ((document.getElementById("odometer-kmsector") !== null)) {
                kmstage.render();
                $("#odometer-kmstage").ready(function() { 
                    kmsector.render();
                    $("#odometer-kmsector").ready(function() { 
                        rePosition();
                    });
                });
            };
        }
        if ((document.getElementById("lineargauge-kmsector") !== null)) {
            $("#lineargauge-kmsector").dxLinearGauge("instance").option("animation.duration", SAMPLE_TIME);
        }
        WebSocket_Send("getAllPoints");
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
            document.getElementsByName("main")[0].style.display = "none";
        }
        set_wss_status("closed");
    }
    wss.onmessage = function(evt) {
        var message = evt.data;
        var values = message.split(':');
        if (values[0] == "data") {
            // mylog(message);
			TIME                  = values[1].replace(/-/g, ":");
			KMH                   = values[2];
			LON                   = values[3];
			LAT                   = values[4];
			HAS_SENSORS           = parseInt(values[5]);
			IS_TIME_SYNC          = (parseInt(values[6]) != 0);
			STAGE_STARTED         = (parseInt(values[7]) != 0);
			STAGE_FRACTIME        = parseInt(values[8]);
			STAGE_TIMETOSTART     = parseInt(values[9]);
			STAGE_TIMETOFINISH    = parseInt(values[10]);
			KM_SECTOR             = STAGE_STARTED?parseFloat(values[11]):0.0;
			KM_SECTOR_PRESET      = parseFloat(values[12]);
			KM_SECTOR_PRESET_REST = parseFloat(values[13]);
			FRAC_SECTOR_DRIVEN    = parseFloat(values[14]);
			KM_STAGE              = STAGE_STARTED?parseFloat(values[15]):0.0;
			KM_RALLYE             = parseFloat(values[16]);
			AVG_KMH               = parseFloat(values[17]);
			DEV_AVG_KMH           = parseFloat(values[18]);
			GPS_MODE              = parseInt(values[19]);
			UBAT                  = parseFloat(values[20]);
			UBAT_CAP              = parseInt(values[21]);
			CPU_TEMP              = parseFloat(values[22]);
			CPU_LOAD              = parseFloat(values[23]);
			DEBUG                 = (parseInt(values[24]) != 0);

            // Bei jedem Aufruf die globale JS Variable setzen 
            if (isset(stageStarted.status)) {
                stageStarted.status = STAGE_STARTED;
            };
            
            if (dashboard) {

                // Seite Tacho
                let speedGauge = $('#circulargauge-speed').dxCircularGauge("instance");
                // Hauptwert: Gerundete aktuelle Geschwindigkeit 
                speedGauge.value(parseInt(KMH));
                // Nebenwert: Durchschnittsgeschwindigkeit oder prozentuale Etappenrestzeit
                if (STAGE_FRACTIME == 0) {
                    speedGauge.subvalues([AVG_KMH]);
                    if (isset(subValueIndicator)) subValueIndicator.color = "gray";
                } else {
                    speedGauge.subvalues([STAGE_FRACTIME]);
                    if (STAGE_FRACTIME < 80) {
                        indicatorColor = "green";
                    } else if (STAGE_FRACTIME < 100) {
                        indicatorColor = "yellow";
                    } else {
                        indicatorColor = "red";
                    }
                    if (isset(subValueIndicator)) subValueIndicator.color = indicatorColor;
                };
                
                // Odometer
                // Etappenstrecke, aus den 10m die 100m _nicht_ runden, sondern abschneiden
                document.getElementById("odometer-kmstage").innerHTML = parseFloat(Math.trunc(KM_STAGE * 10) / 10).toLocaleString('de-DE');
                // Abschnittstrecke
                document.getElementById("odometer-kmsector").innerHTML = parseFloat(KM_SECTOR).toLocaleString('de-DE');
                
                // Linearanzeige: restliche km im Abschnitt
                kmSectorPreset   = KM_SECTOR_PRESET;
                oldLeftInSector  = kmLeftInSector;
                kmLeftInSector   = KM_SECTOR_PRESET_REST;
                diffLeftInSector = kmLeftInSector - oldLeftInSector;

                if (kmSectorPreset > 0) {
                    lineargauge = $("#lineargauge-kmsector").dxLinearGauge("instance")
                    lineargauge.option("value", FRAC_SECTOR_DRIVEN);
                    lineargauge.option("subvalues", [FRAC_SECTOR_DRIVEN]);
                    setKmSector(FRAC_SECTOR_DRIVEN);
                    // Letzter Eintrag vor Stopp
                    if ((kmLeftInSector == 0.0) && (diffLeftInSector != 0.0)) {
                        setTimeout(function() {
                            buttonsToFront();
                        }, 3000);                        
                    } 
                } ;

                // Etappe starten und beenden
                if (STAGE_STARTED) {
                    $("#button-togglestage").dxButton("instance").option("disabled", false);
                } else {
                    if (STAGE_TIMETOSTART > 0) {
                        $("#button-togglestage").dxButton("instance").option("disabled", true);                        
                    } else {
                        $("#button-togglestage").dxButton("instance").option("disabled", (!IS_TIME_SYNC && !DEBUG));                        
                    }
                }

                // Seite GLP
                // Abweichung der durchschnittlichen Geschwindigkeit von der Vorgabe
                devSpeed = $('#circulargauge-devavgspeed').dxCircularGauge("instance");
                devSpeed.value(DEV_AVG_KMH);
                devSpeed.subvalues([DEV_AVG_KMH]);
                
                // Seite Uhr
                // mylog("STAGE_TIMETOSTART: " + STAGE_TIMETOSTART)
                let clock = document.getElementById("clock");
                let smallclock = document.getElementById("smallclock");
                if (STAGE_TIMETOSTART > 0) {
                    if (STAGE_TIMETOSTART < 5*60)
                        clock.style.color = "var(--tm-red)";
                    else if (STAGE_TIMETOSTART < 15*60)
                        clock.style.color = "var(--tm-yellow)";
                    else if (STAGE_TIMETOSTART < 30*60)
                        clock.style.color = "var(--tm-green)";
                    else
                        clock.style.color = "var(--tm-gray)"; 
                    stagetimeto = new Date(STAGE_TIMETOSTART * 1000).toISOString().substr(11, 8);
                    clock.innerHTML = stagetimeto;
                    smallclock.style.display = "block"; 
                    smallclock.style.color = "var(--tm-gray)"; 
                    smallclock.innerHTML = TIME;
                    if (STAGE_TIMETOSTART == 1) {
                        setTimeout(function() {
                            $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 2);
                        }, 900);         
                    }                        
                } else if (STAGE_FRACTIME > 0) {
                    if (STAGE_TIMETOFINISH > 30*60)
                        clock.style.color = "var(--tm-green)";
                    else if (STAGE_TIMETOFINISH > 0)
                        clock.style.color = "var(--tm-yellow)";
                    else
                        clock.style.color = "var(--tm-red)";
                    stagetimeto = new Date(STAGE_TIMETOFINISH * 1000).toISOString().substr(11, 8);
                    if (STAGE_TIMETOFINISH < 0) 
                        stagetimeto = new Date(-STAGE_TIMETOFINISH * 1000).toISOString().substr(11, 8)
                    else
                        stagetimeto = new Date(STAGE_TIMETOFINISH * 1000).toISOString().substr(11, 8)
                    clock.innerHTML = stagetimeto;
                    smallclock.style.display = "block"; 
                    smallclock.style.color = "var(--tm-gray)"; 
                    smallclock.innerHTML = TIME;
                } else {
                    smallclock.style.display = "none";
                    if (IS_TIME_SYNC) {
                    	clock.style.color = "var(--tm-gray)"; 
                  	} else {
                    	clock.style.color = "var(--tm-red)"; 
                  	}
                    clock.innerHTML = TIME;
                }

                // Seite Systemanzeige
                // CPU Temperatur
                $("#circulargauge-cputemp").dxCircularGauge("instance").option("value", CPU_TEMP);
                // Akkuspannung
                $("#circulargauge-ubat").dxCircularGauge("instance").option("value", UBAT);

            };
            
            // GPS
            if(GPS_MODE == 0) {
                color = "var(--tm-lightgray)";
                value = "Kein Signal"
            } else if (GPS_MODE == 1) {
                color = "var(--tm-red)";
                value = "Kein Fix"
            } else if (GPS_MODE == 2) {
                color = "var(--tm-yellow)";
                value = "2D Fix"
            } else if (GPS_MODE == 3) {
                color = "var(--tm-green)";
                value = "3D Fix"
            } else {
                color = "Ivory";
                value = ""
            };
            if (dashboard) {
                document.getElementById("status-gps").style.color = color;
            };
            if (settings) {
            	$("#textbox-gps").dxTextBox("instance").option("value", value)
                $("#textbox-gps").find(".dx-texteditor-input").css("color", color);
            };
            
            // Radsensor(en)
            if(HAS_SENSORS == 0) {
                color = "var(--tm-lightgray)";
            } else if (HAS_SENSORS == 1) {
                color = "var(--tm-red)";
           } else {
                color = "Ivory";
            };
            if (dashboard) {
                document.getElementById("status-tyre").style.color = color;
            };
            
            // Akkuspannung
            cssclass = "status-indicator";
            color    = "var(--tm-green)";
            value    = formatNumber(UBAT, 1) + " Volt"
            if (UBAT_CAP == 5) {
                icon     = "fas fa-plug";
                color    = "var(--tm-lightgray)";
                value    = "Netzteil"
            } else if (UBAT_CAP == 4) {
                icon     = "fas fa-battery-full";
            } else if (UBAT_CAP == 3) {
                icon     = "fas fa-battery-three-quarters";
            } else if (UBAT_CAP == 2) {
                icon     = "fas fa-battery-half";
            } else if (UBAT_CAP == 1) {
                icon     = "fas fa-battery-quarter";
                color    = "var(--tm-yellow)";
            } else {
                icon     = "fas fa-battery-empty";
                color    = "var(--tm-red)";
                cssclass = "status-indicator blink_me";
                if ((UBAT_CAP < 0) && (LASTUBAT_CAP != UBAT_CAP)) {
                    WebSocket_Send("ErrorToAll:Beende Tripmaster in wenigen Sekunden!")
                };
            };
            LASTUBAT_CAP = UBAT_CAP;
            if (dashboard) {
                document.getElementById("status-bat").className   = cssclass
                document.getElementById("status-bat").style.color = color
                document.getElementById("bat-icon").className     = icon
            };
            if (settings) {
            	$("#textbox-ubat").dxTextBox("instance").option("value", value)
                $("#textbox-ubat").find(".dx-texteditor-input").css("color", color);
            };
            
            // CPU Temperatur
            cssclass = "status-indicator";
            if (CPU_TEMP < 60.0) {
                icon     = "fas fa-thermometer-half";
                color    = "var(--tm-green)";
            } else if (CPU_TEMP < 70.0) {
                icon     = "fas fa-thermometer-three-quarters";
                color    = "var(--tm-yellow)";
            } else {
                icon     = "fas fa-thermometer-full";
                color    = "var(--tm-red)";
                cssclass = "status-indicator blink_me";
            };
            if (dashboard) {
                document.getElementById("status-cputemp").className   = cssclass
                document.getElementById("status-cputemp").style.color = color
                document.getElementById("cputemp-icon").className     = icon
            };
            if (settings) {
            	$("#textbox-cputemp").dxTextBox("instance").option("value", formatNumber(CPU_TEMP, 1) + "°C");
                $("#textbox-cputemp").find(".dx-texteditor-input").css("color", color);
            };
            
            // CPU Last
            if (CPU_LOAD < 60.0) {
                color = "var(--tm-green)";
            } else if (CPU_LOAD < 90.0) {
                color = "var(--tm-yellow)";
            } else {
                color = "var(--tm-red)";
            };
            if (dashboard) {
                var statusCPULoad = document.getElementById("status-cpuload").style.color = color;
            };
            if (settings) {
            	$("#textbox-cpuload").dxTextBox("instance").option("value", formatNumber(CPU_LOAD, 1) + " %");
                $("#textbox-cpuload").find(".dx-texteditor-input").css("color", color);
            };
            
            // Entfernungstextboxen
            if (settings) {
                // Abschnitt
                $("#textbox-sector").dxTextBox("instance").option("value", formatDistance(KM_SECTOR));

                // Vorgabe
                let value = "0 m"
                if (KM_SECTOR_PRESET_REST > 0) {
                    value = formatDistance(KM_SECTOR_PRESET)
                }
                $("#textbox-sectorpreset").dxTextBox("instance").option("value", value);

                // Rest
                $("#textbox-sectorpresetrest").dxTextBox("instance").option("value", formatDistance(KM_SECTOR_PRESET_REST));

                // Etappe: Start und Etappe: Ziel
                let stagetimeto = "--:--:--";
                $("#textbox-stagetimeto").find(".dx-texteditor-input").css("color", "");
                if (STAGE_TIMETOSTART > 0) {
                    document.getElementById("label-stagetimeto").innerHTML = "Bis zum Start";
                    stagetimeto = new Date(STAGE_TIMETOSTART * 1000).toISOString().substr(11, 8)
                    $("#textbox-stagetimeto").find(".dx-texteditor-input").css("color", "var(--tm-red)");                    
                } else if (STAGE_FRACTIME > 0) {                    
                    if (STAGE_TIMETOFINISH < 0) {
                        document.getElementById("label-stagetimeto").innerHTML = "Zielzeit überschritten";
                        stagetimeto = new Date(-STAGE_TIMETOFINISH * 1000).toISOString().substr(11, 8)
                        $("#textbox-stagetimeto").find(".dx-texteditor-input").css("color", "var(--tm-red)");                    
                    } else {
                        document.getElementById("label-stagetimeto").innerHTML = "Bis zum Ziel";
                        stagetimeto = new Date(STAGE_TIMETOFINISH * 1000).toISOString().substr(11, 8)
                    }
                }
                
                // Verbleibende Zeit
                $("#textbox-stagetimeto").dxTextBox("instance").option("value", stagetimeto);

                // Etappenstartzeit darf nicht eingegeben werden, wenn Etappe schon läuft
                $("#datebox-stagestart").dxDateBox("instance").option("openOnFieldClick", !STAGE_STARTED);
            
                // Etappe
                $("#textbox-stage").dxTextBox("instance").option("value", formatDistance(KM_STAGE));

                // Rallye
                $("#textbox-rallye").dxTextBox("instance").option("value", formatDistance(KM_RALLYE));
            };

        }
        else if (values[0] == "countdown") {
            // mylog(message);
            var secondsleft = values[1]
            
            // Gibt es sowohl im dashboard als auch bei den settings!
            if (document.getElementById("textbox-regtesttime") !== null) {
                $("#textbox-regtesttime").dxTextBox("instance").option("value", secondsleft + " sek");
            }
            
            if (secondsleft > 0) {
                // if (document.getElementById("textbox-regtestlength") !== null) {
                    // $("#textbox-regtestlength").dxTextBox("instance").option("value", formatDistance(KM_SECTOR_PRESET_REST));
                // }
                if (settings) {
                    // GLP: Abweichung von der idealen Durchschnittsgeschwindigkeit
                    let speedDeviation = formatSpeed(DEV_AVG_KMH);
                    if (DEV_AVG_KMH > 0) speedDeviation = "+" + speedDeviation;
                    $('#textbox-regtestspeed').dxTextBox("instance").option("value", speedDeviation);
                } 
            }
        } else if (values[0] == "avgspeed") {
            // mylog(message);
            if (dashboard) {
                // Seite GLP: Setzen der idealen Durchschnittsgeschwindigkeit
                AVG_KMH_PRESET = parseFloat(values[1]);
                $('#circulargauge-devavgspeed').dxCircularGauge("instance").option("scale.label.customizeText", function(arg) {return formatSpeed(AVG_KMH_PRESET);});
            } 
        } else if (values[0] == "getConfig") {
            // mylog(message);
            var keyvalues = values[1].split('&');
            if (settings) {
                // Konfiguration bearbeiten
                for (var i=0; i<keyvalues.length; i++) {
                    keyvalue = keyvalues[i].split('=');
                    document.getElementById("label-key"+i).innerHTML = keyvalue[0];
                    $("#textbox-key"+i).dxTextBox("instance").option("value", keyvalue[1]);
                };
            } 
        } else {
            // mylog('TM ->: '+message);
        
            TEXT = values[0].replace("&#058;", ":");
            TYPE = values[1]; // ("info", "warning", "error" or "success")
            COMMAND = values[2];
            
            if (values.length == 3) {
                if (COMMAND == "sectorReset") {
                    if (dashboard) {
                        // Anzeige der Abschnittstrecke zurücksetzen
                        let lineargauge = $("#lineargauge-kmsector").dxLinearGauge("instance");
                        lineargauge.option("value", 0);
                        lineargauge.option("subvalues", []);
                    };
                } else if (COMMAND.startsWith("setButtons")) {
                    buttonopts = COMMAND.split("#");
                    let id = buttonopts[1];
                    let icon = buttonopts[2];
                    let iconcolor = buttonopts[3];
                    let button = $("#"+id).dxButton("instance");
                    if (document.getElementById(id) !== null) {
                        button.option({
                            "icon": icon,
                            "elementAttr": {
                                "style": "color: " + iconcolor,
                            },
                        });
                        // Nur die vier "Punkt"-Buttons auf dem Dashboard
                        if ((document.getElementById("multiview-dashboard") !== null) && (id !== "button-togglestage")) {
                            let pointcategory = buttonopts[4];
                            let pointtype = buttonopts[5];
                            if (pointtype == 'null') {
                                button.option("visible", false);
                            } else {
                                button.option("visible", true);
                                button.option({
                                    onClick: function(e) {
                                        audioClick.play().catch(function(error) { });
                                        WebSocket_Send(pointcategory + ":" + pointtype)
                                    },
                                })
                            };
                        };                            
                    };
                // Dateiliste zum Download/Löschen
                } else if (COMMAND.startsWith("downloadfiles")) {
                    if (settings) {
                        let filename = COMMAND.split('#')[1];
                        let filesDataGrid = $("#datagrid-files").dxDataGrid("instance");
                        filesDataGrid.getDataSource().store().insert(
                            {
                                Dateiname: filename,
                            })
                        .done(function (dataObj, key) { /* Process the key and data object here*/ })
                        .fail(function (error) {/* Handle the "error" here */});
                        filesDataGrid.refresh();
                        filesDataGrid.endCustomLoading();
                        $("#popup-download").dxPopup("instance").option("showCloseButton", true);
                    };
                // Punkt in jeweiligem Datagrid anzeigen
                } else if (COMMAND.startsWith("countpointRegistered") || COMMAND.startsWith("checkpointRegistered")) {
                    let pointtype = COMMAND.split("#")[0].replace("Registered", "");
                    if (document.getElementById("datagrid-" + pointtype) !== null) {
                        let pointdata = COMMAND.split('#');
                        let pointDataGrid = $("#datagrid-" + pointtype).dxDataGrid("instance");
                        pointDataGrid.getDataSource().store().insert(
                            {
                                // ID zur Anzeige 1-basiert, im System 0-basiert
                                ID:    parseInt(pointdata[1]) + 1,
                                Name:  pointdata[2],
                                Wert:  pointdata[3],
                                Aktiv: pointdata[4] == 1?true:false,
                            })
                        .done(function (dataObj, key) { /* Process the key and data object here*/ })
                        .fail(function (error) {/* Handle the "error" here */});
                        pointDataGrid.refresh();
                        // Wenn eine OK eingegeben wurde, zur Seite mit Datagrid springen wg Dateneingabe
                        if ((pointtype == "checkpoint") && (document.getElementById("tabpanel-settings") !== null)) {
                            $("#tabpanel-settings").dxTabPanel("instance").option("selectedIndex", 2)
                            if (isset(jumpToLastPage)) jumpToLastPage = true;
                        };
                    };
                };
                if (dashboard) {
                    // Automatische Auswahl der Seite je nach Befehl
                    if (COMMAND == "switchToClock") {
                        $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 1);
                    } else if (COMMAND == "switchToMain") {
                        $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 2);
                    } else if (COMMAND == "regTestStarted") {
                        $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 3);
                    } else if (COMMAND == "regTestStopped") {
                        setTimeout(function() {
                            $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 2);
                            AVG_KMH_PRESET = 0;
                            $('#circulargauge-devavgspeed').dxCircularGauge("instance").option("scale.label.customizeText", function(arg) {
                                return formatSpeed(AVG_KMH_PRESET);
                            });
                        }, 2000);
                    } else if ((COMMAND == "sectorReset") || (COMMAND == "sectorLengthreset")) {
                        setTimeout(function() {
                            buttonsToFront();
                        }, 2000);                        
                    } else if (COMMAND == "sectorLengthset") {
                        if (document.getElementById("button-group") !== null) {
                            $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 2)
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
        // mylog('-> TM: '+data);
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
    }
}
