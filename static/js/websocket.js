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
            $('#circulargauge-speed').dxCircularGauge("instance").option("animation.duration", SAMPLE_TIME);
            if ((document.getElementById("odometer-kmsector") !== null)) {
                kmstage.render();
                $("#odometer-kmstage").ready(function() { 
                    kmsector.render();
                    $("#odometer-kmsector").ready(function() { 
                        resizeAndPosition();
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
            // 1,    2,    3,   4        5,        6,        7,         8,                9,                     10,               
            // TIME, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_STAGE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, 
            // 11,          12,       13,  14,  15,          16,           17,            18,             19,                20
            // DEV_AVG_KMH, GPS_MODE, LON, LAT, HAS_SENSORS, IS_TIME_SYNC, STAGE_STARTED, STAGE_FRACTIME, STAGE_TIMETOSTART, STAGE_TIMETOFINISH
            // 21
            // CPU_TEMP
            TIME                  = values[1].replace(/-/g, ":");; 
            KMH                   = values[3]; 
            AVG_KMH               = parseFloat(values[4]); 
            KM_RALLYE             = parseFloat(values[5]);
            KM_STAGE              = parseFloat(values[6]);
            KM_SECTOR             = parseFloat(values[7]);
            KM_SECTOR_PRESET      = parseFloat(values[8]);
            KM_SECTOR_PRESET_REST = parseFloat(values[9]);
            FRAC_SECTOR_DRIVEN    = parseFloat(values[10]);
            DEV_AVG_KMH           = parseFloat(values[11]);
            GPS_MODE              = parseInt(values[12]); 
            LON                   = values[13]; 
            LAT                   = values[14]; 
            HAS_SENSORS           = parseInt(values[15]);
            IS_TIME_SYNC          = parseInt(values[16]);
            STAGE_STARTED         = (parseInt(values[17]) != 0), 
            STAGE_FRACTIME        = parseInt(values[18]), 
            STAGE_TIMETOSTART     = parseInt(values[19]);
            STAGE_TIMETOFINISH    = parseInt(values[20]);
            CPU_TEMP              = parseFloat(values[21]);

            // Tacho
            if (document.getElementById("circulargauge-speed") !== null) {
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
            }; 
            // Odometer, mit , als Dezimaltrennzeichen
            if (document.getElementById("odometer-kmstage") !== null) {
                // aus den 10m die 100m _nicht_ runden, sondern abschneiden
                KM_STAGE_TRUNC = Math.trunc(KM_STAGE * 10) / 10;
                document.getElementById("odometer-kmstage").innerHTML = parseFloat(KM_STAGE_TRUNC).toLocaleString('de-DE');
            } 
            if (document.getElementById("odometer-kmsector") !== null) {
                let odometerKmSector = document.getElementById("odometer-kmsector");
                // Wenn Abschnittsvorgabe eingestellt..
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
                kmSectorPreset = KM_SECTOR_PRESET;
                oldLeftInSector = kmLeftInSector;
                kmLeftInSector = KM_SECTOR_PRESET_REST;
                diffLeftInSector = kmLeftInSector - oldLeftInSector;
                // mylog("kmSectorPreset: " + kmSectorPreset);
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
            } 
            // Statusanzeige: GPS
            if (document.getElementById("status-gps") !== null) {
                switch(GPS_MODE) {
                    case 0:
                        fontColor = "var(--tm-lightgray)";
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

                switch(HAS_SENSORS) {
                    case 0:
                        fontColor = "var(--tm-lightgray)";
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
                if (STAGE_STARTED) {
                    $("#button-togglestage").dxButton("instance").option("disabled", false);
                } else {
                    if (STAGE_TIMETOSTART > 0) {
                        $("#button-togglestage").dxButton("instance").option("disabled", true);                        
                    } else {
                        $("#button-togglestage").dxButton("instance").option("disabled", (IS_TIME_SYNC == 0));                        
                    }
                }
            };
            // Bei jedem Aufruf die globale JS Variable setzen 
            if (isset(stageStarted.status)) {
                stageStarted.status = STAGE_STARTED;
            };
            
            // Etappestart- und -zielzeit
            if (document.getElementById("textbox-stagetimeto") !== null) {
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
                $("#textbox-stagetimeto").dxTextBox("instance").option("value", stagetimeto);
            };            
            if (document.getElementById("datebox-stagestart") !== null) {
                // Etappenstartzeit darf nicht eingegeben werden, wenn Etappe schon läuft
                $("#datebox-stagestart").dxDateBox("instance").option("openOnFieldClick", !STAGE_STARTED);
            };
            
            // Anzeige auf der Uhr
            if (document.getElementById("clock") !== null) {
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
                            $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 1);
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
                    clock.style.color = "var(--tm-gray)"; 
                    clock.innerHTML = TIME;
                }
            };
            
            // Entfernungstextboxen
            // Abschnittsvorgabe
            if (document.getElementById("textbox-sectorpreset") !== null) {
                let value = "0 m"
                if (KM_SECTOR_PRESET_REST > 0) {
                    value = formatDistance(KM_SECTOR_PRESET)
                }
                $("#textbox-sectorpreset").dxTextBox("instance").option("value", value);
            };
            // Verbleibende Abschnittsvorgabe
            if (document.getElementById("textbox-sectorpresetrest") !== null) {
                $("#textbox-sectorpresetrest").dxTextBox("instance").option("value", formatDistance(KM_SECTOR_PRESET_REST));
            };
            // Abschnitt
            if (document.getElementById("textbox-sector") !== null) {
                $("#textbox-sector").dxTextBox("instance").option("value", formatDistance(KM_SECTOR));
            };
            // Etappe
            if (document.getElementById("textbox-stage") !== null) {
                $("#textbox-stage").dxTextBox("instance").option("value", formatDistance(KM_STAGE));
            };
            // Gesamt
            if (document.getElementById("textbox-rallye") !== null) {
                $("#textbox-rallye").dxTextBox("instance").option("value", formatDistance(KM_RALLYE));
            };
            // Abweichung der durchschnittlichen Geschwindigkeit von der Vorgabe
            if ((document.getElementById("circulargauge-devavgspeed") !== null)) {
                devSpeed = $('#circulargauge-devavgspeed').dxCircularGauge("instance");
                devSpeed.value(DEV_AVG_KMH);
                devSpeed.subvalues([DEV_AVG_KMH]);
            };
            // CPU Temperatur des RasPi
            if ((document.getElementById("textbox-cputemp") !== null)) {
                if($("#textbox-cputemp").dxTextBox("instance").option("visible") == true) {
                    $("#textbox-cputemp").dxTextBox("instance").option("value", CPU_TEMP);
                };
            };
            if ((document.getElementById("circulargauge-cputemp") !== null)) {
                $("#circulargauge-cputemp").dxCircularGauge("instance").option("value", CPU_TEMP);
            };
        }
        else if (values[0] == "countdown") {
            // mylog(message);
            var secondsleft = values[1]
            if (document.getElementById("textbox-regtesttime") !== null) {
                $("#textbox-regtesttime").dxTextBox("instance").option("value", secondsleft + " sek");
            }
            if (secondsleft > 0) {
                if (document.getElementById("textbox-regtestlength") !== null) {
                    $("#textbox-regtestlength").dxTextBox("instance").option("value", formatDistance(KM_SECTOR_PRESET_REST));
                }
                if (document.getElementById("textbox-regtestspeed") !== null) {
                    let speedDeviation = formatSpeed(DEV_AVG_KMH);
                    if (DEV_AVG_KMH > 0) speedDeviation = "+" + speedDeviation;
                    $('#textbox-regtestspeed').dxTextBox("instance").option("value", speedDeviation);
                } 
            }
        } else if (values[0] == "avgspeed") {
            // mylog(message);
            if (document.getElementById("circulargauge-devavgspeed") !== null) {
                AVG_KMH_PRESET = parseFloat(values[1]);
                $('#circulargauge-devavgspeed').dxCircularGauge("instance").option("scale.label.customizeText", function(arg) {return formatSpeed(AVG_KMH_PRESET);});
            } 
        } else if (values[0] == "getConfig") {
            // mylog(message);
            var keyvalues = values[1].split('&');
            if (document.getElementById("popup-editconfiguration") !== null) {
                for (var i=0; i<keyvalues.length; i++) {
                    keyvalue = keyvalues[i].split('=');
                    document.getElementById("label-key"+i).innerHTML = keyvalue[0];
                    $("#textbox-key"+i).dxTextBox("instance").option("value", keyvalue[1]);
                };
            } 
        } else {
            mylog('TM ->: '+message);
        
            TEXT = values[0].replace("&#058;", ":");
            TYPE = values[1]; // ("info", "warning", "error" or "success")
            COMMAND = values[2];
            
            if (values.length == 3) {
                if (COMMAND == "sectorReset") {
                    if (document.getElementById("lineargauge-kmsector") !== null) {
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
                    if (document.getElementById("datagrid-files") !== null) {
                        let filename = COMMAND.split('#')[1];
                        let filesDataGrid = $("#datagrid-files").dxDataGrid("instance");
                        filesDataGrid.getDataSource().store().insert(
                            {
                                Dateiname: filename,
                            })
                        .done(function (dataObj, key) { /* Process the key and data object here*/ })
                        .fail(function (error) {/* Handle the "error" here */});
                        filesDataGrid.refresh();
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
                            $("#tabpanel-settings").dxTabPanel("instance").option("selectedIndex", 3)
                            if (isset(jumpToLastPage)) jumpToLastPage = true;
                        };
                    };
                };
                // Nur Dashboard
                if (document.getElementById("multiview-dashboard") !== null) {
                    if (COMMAND == "switchToClock") {
                        $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 0);
                    } else if (COMMAND == "switchToMain") {
                        $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 1);
                    } else if (COMMAND == "regTestStarted") {
                        $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 2);
                    } else if (COMMAND == "regTestStopped") {
                        setTimeout(function() {
                            $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 1);
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
                            $("#multiview-dashboard").dxMultiView("instance").option("selectedIndex", 1)
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
        mylog('-> TM: '+data);
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
