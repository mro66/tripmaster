var audioElement = document.createElement('audio');
audioElement.setAttribute('src', '/static/Wine_Glass.ogg');
var countdownRunning = false;

var checkpointList = [{
        "Variable": "null",
        "Name": "Keine",
        "Icon": "fas fa-minus",
        "Iconfarbe": "var(--tm-red)"
    },{
        "Variable": "roundabout",
        "Name": "Kreisverkehr",
        "Icon": "fas fa-sync",
        "Iconfarbe": "var(--tm-blue)"
    }, {
        "Variable": "townsign",
        "Name": "Ortsschild",
        "Icon": "fas fa-sign",
        "Iconfarbe": "var(--tm-yellow)"
    }, {
        "Variable": "stampcheck",
        "Name": "Stempelkontrolle",
        "Icon": "fas fa-stamp",
        "Iconfarbe": "var(--tm-red)"
    }, {
        "Variable": "mutecheck",
        "Name": "Stummer Wächter",
        "Icon": "fas fa-neuter",
        "Iconfarbe": "var(--tm-green)"
    }, {
        "Variable": "checkpoint",
        "Name": "Sonstiges",
        "Icon": "fas fa-map-marker-alt",
        "Iconfarbe": "var(--tm-green)"
    }];

var countpointList = [{
        "Variable": "null",
        "Name": "Keine",
        "Icon": "fas fa-minus",
        "Iconfarbe": "var(--tm-red)"
    },{
        "Variable": "roundabout",
        "Name": "Kreisverkehr",
        "Icon": "fas fa-sync",
        "Iconfarbe": "var(--tm-blue)"
    }, {
        "Variable": "countpoint",
        "Name": "Sonstiges",
        "Icon": "fas fa-hashtag",
        "Iconfarbe": "var(--tm-blue)"
    }];
// Zahlenfeld mit <<, <, >, >>
var numberBoxOptions = {
    inputAttr: {
        style: "font-size: 4vmax; text-align: center",
    },
    min: 0,
    value: 0,
    buttons: [
        {
            name: "doubledown",
            location: "before",
            focusStateEnabled: false,
            hoverStateEnabled: false,
            options: {
                icon: "fas fa-angle-double-left",
            },
        },
        {
            name: "down",
            location: "before",
            focusStateEnabled: false,
            hoverStateEnabled: false,
            options: {
                icon: "fas fa-angle-left",
            },
        },
        {
            name: "doubleup",
            focusStateEnabled: false,
            hoverStateEnabled: false,
            options: {
                icon: "fas fa-angle-right",
            },
        },
        {
            name: "up",
            focusStateEnabled: false,
            hoverStateEnabled: false,
            options: {
                icon: "fas fa-angle-double-right",
            },
        },
    ]
};

var dataGridOptions = {
    elementAttr: {
        style: "font-size: 3vmax",
    },
    dataSource: [
    ],
    keyExpr: "ID",
    editing: {
        mode: "cell",
        allowUpdating: true,
        selectTextOnEditStart: true,
        texts: {
            cancelRowChanges: "Abbrechen",
            editRow: "Bearbeiten",
            saveRowChanges: "Speichern"
        },
        useIcons: true,
    },
    noDataText: "Keine Daten vorhanden",
    paging: {
        pageSize: 12,
    },
}

$(function(){

// TabPanel 

     $("#tabpanel-settings").dxTabPanel({
        deferRendering: false,
        height: "100%",
        loop: true,
        selectedIndex: 0,
        items: [{
            // Abschnitt
            "title": [],
            icon: "fas fa-route",
            template: $("#tab-sector"),
        }, {
            // GLP
            "title": [],
            icon: "fas fa-stopwatch",
            template: $("#tab-regtest"),
        }, {
            // Bordkarte - Zählpunkte
            title: [],
            icon: "fas fa-hashtag",
            template: $("#tab-countpoint"),
        }, {
            // Bordkarte - Orientierungskontrollen
            title: [],
            icon: "fas fa-map-marker-alt",
            template: $("#tab-checkpoint"),
        }, {
            // Settings
            "title": [],
            icon: "fas fa-cogs",
            template: $("#tab-setup"),
        }],
        onSelectionChanged: function(e) {
            if (e.component.option("selectedIndex")==0) {
                $("#textbox-sector").appendTo("#tab0_sector");
            } else if (e.component.option("selectedIndex")==2) {
                $("#textbox-sector").appendTo("#tab2_sector");
            }
        }
    });

// Tab Abschnitt

    var sectorPresetNumberBox = $("#numberbox-sectorpreset").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 25,
        step: 0.05,
        format: "#0.00 km",
        onValueChanged: function(e) {
            $("#button-setsector").dxButton("instance").option("disabled", (e.value === 0.0) || !stageStarted);
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        let newval = sectorPresetNumberBox.option("value") - 1;
                        if (newval <= sectorPresetNumberBox.option("min")) {
                            sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("min"));
                        } else {
                            sectorPresetNumberBox.option("value", newval);
                        }
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = sectorPresetNumberBox.option("value") - .05;
                        if (newval <= sectorPresetNumberBox.option("min")) {
                            sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("min"));
                        } else {
                            sectorPresetNumberBox.option("value", newval);
                        }
                    },
                }
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = sectorPresetNumberBox.option("value") + .05;
                        if (newval >= sectorPresetNumberBox.option("max")) {
                            sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("max"));
                        } else {
                            sectorPresetNumberBox.option("value", newval);
                        }
                    },
                  }
            },
            {
                options: {
                    onClick: function(e) {
                        let newval = sectorPresetNumberBox.option("value") + 1;
                        if (newval >= sectorPresetNumberBox.option("max")) {
                            sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("max"));
                        } else {
                            sectorPresetNumberBox.option("value", newval);
                        }
                    }
                }
            }
        ],
    })).dxNumberBox("instance");

    $("#button-setsector").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-check",
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onClick: function(e) {
            let sectorLength = parseFloat(sectorPresetNumberBox.option("value")); //.toFixed(2); 
            setReverse(false);
            WebSocket_Send('setSectorLength:'+sectorLength);
            sectorPresetNumberBox.option("value", 0);
        },
    })) 

    $("#button-resetsector").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-undo-alt",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            resetSector();
        },
    })); 

        function resetSector() {
            sectorPresetNumberBox.option("value", 0);
            sectorTextbox.option("value", formatDistance(0));
            sectorPresetTextbox.option("value", "0 m");
            sectorPresetRestTextbox.option("value", "0 m");
            setReverse(false);
            if (stageStarted)
                WebSocket_Send('resetSector');
        }

    var reverseButton = $("#button-reverse").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-arrow-up",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onContentReady: function(e) {
            // setReverse(false);
        },
        onClick: function(e) {
            WebSocket_Send("toggleReverse");
            setReverse(e.component.option("icon") === "fas fa-arrow-up");
        },
    })).dxButton("instance");
    
        function setReverse(backwards) {
            if (backwards) {
                reverseButton.option("icon", "fas fa-arrow-down");
                reverseButton.option("elementAttr", {"style": "color: var(--tm-red)"});
                // Wenn rückwärts, dann roter Text
                $("#textbox-sector").find(".dx-texteditor-input").css("color", "var(--tm-red)");					
            } else {
                reverseButton.option("icon", "fas fa-arrow-up");
                reverseButton.option("elementAttr", {"style": "color: var(--tm-green)"});
                $("#textbox-sector").find(".dx-texteditor-input").css("color", "");					
            };          
        };
 
    var sectorTextbox = $("#textbox-sector").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: formatDistance(0),
        onValueChanged: function(e) {
            if (isSoundEnabled()) {
                actValue = unformatDistance(e.value);
                prevValue = unformatDistance(e.previousValue);
                presetValue = unformatDistance(sectorPresetTextbox.option("value"));
                if ((actValue >= presetValue) && (prevValue < presetValue)) {
                    // Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
                    audioElement.play().catch(function(error) { });
                }
            }
        },
    })).dxTextBox("instance");

    var sectorPresetTextbox = $("#textbox-sectorpreset").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
    })).dxTextBox("instance");

    var sectorPresetRestTextbox = $("#textbox-sectorpresetrest").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
    })).dxTextBox("instance");

    $("#datebox-stageend").dxDateBox({
        placeholder: "00:00",
        showClearButton: true,
        displayFormat: "HH:mm",
        pickerType: "rollers",
        type: "time",
        onValueChanged: function(e) {
            let stageend = e.component.option("value");
            if (stageend != null) {
                stageend.setSeconds(0)
                stageend.setMilliseconds(0);
                stageend = stageend.getTime();
            }
            WebSocket_Send("setStageTime:"+stageend)
        },
    });

    var timeInStageTextbox = $("#textbox-timeinstage").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "00:00",
    })).dxTextBox("instance");

// Tab GLP

    var setRegtestButton = $("#button-setregtest").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-check",
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onClick: function(e) {
            if (countdownRunning == false) {
                resetSector();
                WebSocket_Send('startRegtest:'+getRegtestTime());
                if (getRegtestLength() > 0) {
                    WebSocket_Send('setSectorLength:'+getRegtestLength());						
                };
                if (getRegtestAvgSpeed() > 0) {
                    WebSocket_Send('setAvgSpeed:'+getRegtestAvgSpeed());
                };
                countdownRunning = true;
                // Stopzeichen
                e.component.option("icon", "far fa-times-circle");
                e.component.option("elementAttr", {"style": "color: var(--tm-red)"});
                resetRegtestButton.option("disabled", true);
                $("#textbox-regtesttime").find(".dx-texteditor-input").css("color", "var(--tm-red)");
            } else {
                WebSocket_Send('stopRegtest');
                resetRegtest(false);
                setTimeout(resetSector, 2000);
            }				
        },
    })).dxButton("instance"); 

    var resetRegtestButton = $("#button-resetregtest").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-undo-alt",
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            resetRegtest(false);
        },
    })).dxButton("instance"); 

        function resetRegtest(flicker = true) {
            countdownRunning = false;
            setRegtestButton.option("icon", "fas fa-check");
            setRegtestButton.option("elementAttr", {"style": "color: var(--tm-green)"});
           // reset regtestStartTimeNumberbox
            regtestLengthNumberBox.option("value", 0);
            regtestTimeNumberbox.option("value", 0);
            // setRegtestAvgSpeed();
            
            var countdownText = document.getElementById("textbox-regtesttime").children[0].children[0].children[0];
            if (flicker) {
                countdownText.classList.remove("flicker");
                countdownText.classList.remove("secondyellow", "secondred");
                void countdownText.offsetWidth;
                countdownText.classList.add("flicker");
            }
            countdownText.style.color = "black";
        };

    // Zeitvorgabe

    var regtestTimeNumberbox = $("#numberbox-regtesttime").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 1200,
        step: 1,
        format: "#0 sek",
        onValueChanged: function (e) {
            setRegtestTime();
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        let newval = regtestTimeNumberbox.option("value") - 20;
                        if (newval <= regtestTimeNumberbox.option("min")) {
                            regtestTimeNumberbox.option("value", regtestTimeNumberbox.option("min"));
                        } else {
                            regtestTimeNumberbox.option("value", newval);
                        }
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = regtestTimeNumberbox.option("value") - regtestTimeNumberbox.option("step");
                        if (newval <= regtestTimeNumberbox.option("min")) {
                            regtestTimeNumberbox.option("value", regtestTimeNumberbox.option("min"));
                        } else {
                            regtestTimeNumberbox.option("value", newval);
                        }
                    },
                }
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = regtestTimeNumberbox.option("value") + regtestTimeNumberbox.option("step");
                        if (newval >= regtestTimeNumberbox.option("max")) {
                            regtestTimeNumberbox.option("value", regtestTimeNumberbox.option("max"));
                        } else {
                            regtestTimeNumberbox.option("value", newval);
                        }
                    },
                  }
            },
            {
                options: {
                    onClick: function(e) {
                        let newval = regtestTimeNumberbox.option("value") + 20;
                        if (newval >= regtestTimeNumberbox.option("max")) {
                            regtestTimeNumberbox.option("value", regtestTimeNumberbox.option("max"));
                        } else {
                            regtestTimeNumberbox.option("value", newval);
                        }
                    }
                }
            }
        ],
    })).dxNumberBox("instance");

        function getRegtestTime() {
            return parseInt(regtestTimeNumberbox.option("value"))
        };

        function setRegtestTime() {
            var regtestTime = getRegtestTime();
            regtestTimeTextbox.option("value", regtestTime + " sek");
            if (regtestTime > 0) {
                resetRegtestButton.option("disabled", false);
                if (stageStarted)
                    setRegtestButton.option("disabled", false);
                // setRegtestStartTime();
            } else {
                resetRegtestButton.option("disabled", true);
                setRegtestButton.option("disabled", true);
            }
            setRegtestAvgSpeed();
        };
   
    // Strecke

    var regtestLengthNumberBox = $("#numberbox-regtestlength").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 25,
        step: 0.05,
        format: "#0.00 km",
        onValueChanged: function(e) {
            setRegtestLength();
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        let newval = regtestLengthNumberBox.option("value") - 1;
                        if (newval <= regtestLengthNumberBox.option("min")) {
                            regtestLengthNumberBox.option("value", regtestLengthNumberBox.option("min"));
                        } else {
                            regtestLengthNumberBox.option("value", newval);
                        }
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = regtestLengthNumberBox.option("value") - .05;
                        if (newval <= regtestLengthNumberBox.option("min")) {
                            regtestLengthNumberBox.option("value", regtestLengthNumberBox.option("min"));
                        } else {
                            regtestLengthNumberBox.option("value", newval);
                        }
                    },
                }
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = regtestLengthNumberBox.option("value") + .05;
                        if (newval >= regtestLengthNumberBox.option("max")) {
                            regtestLengthNumberBox.option("value", regtestLengthNumberBox.option("max"));
                        } else {
                            regtestLengthNumberBox.option("value", newval);
                        }
                    },
                  }
            },
            {
                options: {
                    onClick: function(e) {
                        let newval = regtestLengthNumberBox.option("value") + 1;
                        if (newval >= regtestLengthNumberBox.option("max")) {
                            regtestLengthNumberBox.option("value", regtestLengthNumberBox.option("max"));
                        } else {
                            regtestLengthNumberBox.option("value", newval);
                        }
                    }
                }
            }
        ],
    })).dxNumberBox("instance");
      
        function getRegtestLength() {
            return parseFloat(regtestLengthNumberBox.option("value")); //.toFixed(2); 
        };
        
        function setRegtestLength() {
            var regtestLength = getRegtestLength();
            regtestLengthTextbox.option("value", formatDistance(regtestLength));
            if (regtestLength > 0) {
                resetRegtestButton.option("disabled", false);
                // ohne Zeit keine GLP
                // setRegtestButton.option("disabled", false);
                // setRegtestStartTime();
            } else {
                resetRegtestButton.option("disabled", true);
                // ohne Zeit keine GLP
                // setRegtestButton.option("disabled", true);
            }
            setRegtestAvgSpeed();
        };


    /* Startzeit (TODO: nicht fertig implementiert)
    
    var regtestStartHourNumberbox = $("#numberbox-regteststarthour").dxNumberBox({
        min: -1, max: 24,
        value: 0,
        step: 1,
        format: "#0 h",
        showSpinButtons: true,
        useLargeSpinButtons: false,
        onValueChanged: function (e) {
            if (e.value == e.component.option("max")) {
                e.component.option("value", 0);
            } else if (e.value == e.component.option("min")) {
                e.component.option("value", e.component.option("max")-e.component.option("step"));
            } else if (e.value == null) {
                e.component.option("value", 0);
            }
            setRegtestStartTime();
        },
    }).dxNumberBox("instance");
        
    var regtestStartMinuteNumberbox = $("#numberbox-regteststartminute").dxNumberBox({
        min: -1, max: 60,
        value: 0,
        step: 1,
        format: "#0 min",
        showSpinButtons: true,
        useLargeSpinButtons: false,
        onValueChanged: function (e) {
            if (e.value == e.component.option("max")) {
                e.component.option("value", 0);
                regtestStartHourNumberbox.option("value", regtestStartHourNumberbox.option("value")+1);
            } else if (e.value == e.component.option("min")) {
                e.component.option("value", e.component.option("max")-e.component.option("step"));
                regtestStartHourNumberbox.option("value", regtestStartHourNumberbox.option("value")-1);
            } else if (e.value == null) {
                e.component.option("value", 0);
            }					
            setRegtestStartTime();
        },
    }).dxNumberBox("instance");
        
    var regtestStartSecondNumberbox = $("#numberbox-regteststartsecond").dxNumberBox({
        min: -1, max: 60,
        value: 0,
        step: 1,
        format: "#0 s",
        showSpinButtons: true,
        useLargeSpinButtons: false,
        onValueChanged: function (e) {
            if (e.value == e.component.option("max")) {
                e.component.option("value", 0);
                regtestStartMinuteNumberbox.option("value", regtestStartMinuteNumberbox.option("value")+1);
            } else if (e.value == e.component.option("min")) {
                e.component.option("value", e.component.option("max")-e.component.option("step"));
                regtestStartMinuteNumberbox.option("value", regtestStartMinuteNumberbox.option("value")-1);
            } else if (e.value == null) {
                e.component.option("value", 0);
            }					
            setRegtestStartTime();
        },		
    }).dxNumberBox("instance");

    function getRegtestStartTime() {
        var startHour = regtestStartHourNumberbox.option("value");
        var startMinute = regtestStartMinuteNumberbox.option("value");
        var startSecond = regtestStartSecondNumberbox.option("value");
        if ((startHour + startMinute + startSecond) > 0) {
            var startDate = new Date(); 
            startDate.setHours  (startHour);
            startDate.setMinutes(startMinute);
            startDate.setSeconds(startSecond);
            return startDate;
        } else {
            return 0;
        };
    };			

    function setRegtestStartTime() {
        if (setRegtestButton.option("disabled") == false) {
            startDate = 0; //getRegtestStartTime();
            if (startDate > 0) {
                setRegtestButton.option("text", "Um "+startDate.toTimeString().split(' ')[0]+" starten");	
            } else {
                setRegtestButton.option("text", "Starten"); //"Manuell starten");
            };
        };
    };			
    */
    
    // Anzeige
    
    var regtestTimeTextbox = $("#textbox-regtesttime").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 sek",
        onValueChanged: function(e) {
            var countdownText = document.getElementById("textbox-regtesttime").children[0].children[0].children[0];
            var myValue = parseInt(e.value);
            regtestMinutesDecimalTextbox.option("value", formatNumber(myValue/60) + " min");
            let sek = "0" + myValue % 60;
            regtestMinutesTextbox.option("value", parseInt(myValue/60) + ":" + sek.substr(sek.length - 2) + " min");
            if (countdownRunning == true) {
                if (myValue > 0) {
                    regtestLengthTextbox.option("value", formatDistance(kmLeftInSector));
                    animationClass = "secondyellow";
                    countdownText.style.color = "var(--tm-red)";
                    if (myValue <= 10) {
                        if (myValue <= 5) {
                            animationClass = "secondred";
                        };
                        countdownText.classList.remove("flicker");
                        countdownText.classList.remove(animationClass);
                        void countdownText.offsetWidth;
                        countdownText.classList.add(animationClass);
                    };
                } else {
                    if (isSoundEnabled()) {
                        audioElement.play().catch(function(error) { });
                    };
                    resetRegtest();
                    setTimeout(resetSector, 2000);
                }
            };
        },
    })).dxTextBox("instance");
    
    var regtestMinutesTextbox = $("#textbox-regtestminutes").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0:00 min",
    })).dxTextBox("instance");
    
    var regtestMinutesDecimalTextbox = $("#textbox-regtestminutesdecimal").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0,00 min",
    })).dxTextBox("instance");
    
    var regtestLengthTextbox = $("#textbox-regtestlength").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
    })).dxTextBox("instance");
            
    var regtestAvgSpeedTextbox = $("#textbox-regtestavgspeed").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: formatSpeed(0),
    })).dxTextBox("instance");
    
        function getRegtestAvgSpeed() {
            var regtestLength = getRegtestLength();
            var regtestTime = getRegtestTime();
            return regtestLength / regtestTime * 60 * 60;
        };
        
        function setRegtestAvgSpeed() {
            var regtestLength = getRegtestLength();
            var regtestTime = getRegtestTime();
            if ((regtestLength > 0) && (regtestTime > 0)) {
                regtestAvgSpeedTextbox.option("value", formatSpeed(regtestLength / regtestTime * 60 * 60));
            } else {
                regtestAvgSpeedTextbox.option("value", formatSpeed(0));
            }
        };

// Tab Zählpunkte

    $("#datagrid-countpoint").dxDataGrid($.extend(true, {}, dataGridOptions, {
        columns: [
            {
                dataField: "ID",
                allowEditing: false,
                width: "6vmax",
            },
            {
                dataField: "Beschreibung",
                allowEditing: false,
            },
            {
                dataField: "Sicher",
                dataType: "boolean",
                caption: "OK",
                width: "10vmax",
            },
        ],
        summary: {
            totalItems: [
                {
                    column: "Sicher",
                    summaryType: "sum",
                    showInColumn: "Beschreibung",
                }
            ],
            texts: {
                sumOtherColumn: "Anzahl: {0}"
            }
        },
        onRowUpdated: function(e) {
            id = e.data.ID;
            description = e.data.Beschreibung;
            name = e.data.Name;
            visibility = e.data.Sicher;
            WebSocket_Send("changepoint:countpoint&"+id+"&"+description+"&"+name+"&"+(visibility?1:0));
        },
    }));

    $("#selectbox-countpoint").dxSelectBox({
        dataSource: countpointList,
        displayExpr: "Name",
        valueExpr: "Variable",
        value: "roundabout"
    });

// Tab Orientierungskontrollen

    $("#datagrid-checkpoint").dxDataGrid($.extend(true, {}, dataGridOptions, {
        columns: [
            {
                dataField: "ID",
                allowEditing: false,
                width: "6vmax",
            },
            {
                dataField: "Beschreibung",
                allowEditing: false,
                lookup: {
                    dataSource: checkpointList,
                    displayExpr: "Name",
                    valueExpr: "ID"
                }
            },
            {
                dataField: "Name",
                allowEditing: true,
                width: "12vmax",
            },
            {
                dataField: "Sicher",
                dataType: "boolean",
                caption: "OK",  
                width: "10vmax",
            },
        ],
        onRowUpdated: function(e) {
            id = e.data.ID;
            description = e.data.Beschreibung;
            
            e.data.Name = e.data.Name.toUpperCase();
            
            name = e.data.Name;
            visibility = e.data.Sicher;           
            WebSocket_Send("changepoint:checkpoint&"+id+"&"+description+"&"+name+"&"+(visibility?1:0));
        },
    }));

    $("#selectbox-checkpoint").dxSelectBox({
        dataSource: checkpointList,
        displayExpr: "Name",
        valueExpr: "Variable",
        value: "townsign",
        onSelectionChanged: function(e) {
            // v = e.data.Variable;
            // n = e.data.Name;
            // i = e.data.Icon;
            // c = e.data.Iconfarbe;
            // mylog(v); mylog(n); mylog(i); mylog(c);
        },
    });

// Tab Setup

    // RasPi - Reboot
    $("#button-sudoreboot").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-redo",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
            confirmDialog("RasPi neu starten").show().done(function (dialogResult) {
                if (dialogResult) {
                    WebSocket_Send('sudoReboot');
                }
            });
        },
    })); 
    
    // RasPi - Halt
    $("#button-sudohalt").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-power-off",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            confirmDialog("RasPi anhalten").show().done(function (dialogResult) {
                if (dialogResult) {
                    WebSocket_Send('sudoHalt');
                }
            });
        },
    })); 

    // Tripmaster - Sound
    var toggleSoundButton = $("#button-togglesound").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-volume-mute",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            if (isSoundEnabled()) {
                toggleSoundButton.option("icon", "fas fa-volume-mute");
                toggleSoundButton.option("elementAttr", {"style": "color: var(--tm-red)"});
            } else {
                toggleSoundButton.option("icon", "fas fa-volume-up");
                toggleSoundButton.option("elementAttr", {"style": "color: var(--tm-green)"});
                // Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
                audioElement.play().catch(function(error) { });
            };
        },
    })).dxButton("instance");

        function isSoundEnabled() {
            return toggleSoundButton.option("icon") === "fas fa-volume-up"
        };

    // Tripmaster - Reset
    $("#button-resettripmaster").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-redo",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
            confirmDialog("Reset Tripmaster").show().done(function (dialogResult) {
                if (dialogResult) {
                    WebSocket_Send('resetTripmaster');
                    stageTextbox.option("value", formatDistance(0));
                    totalTextbox.option("value", formatDistance(0));
                }
            });
        },
    })); 


    var configurationSelectBox = $("#selectbox-configuration").dxSelectBox({
        dataSource: [
            "Jaguar",
            "Audi",
            "Trabant"
        ],
        value: ACTIVE_CONFIG,
        onValueChanged: function(e) {
            WebSocket_Send('changeConfig:'+e.component.option("value"));
        }
    }).dxSelectBox("instance");
            
    $("#button-editconfiguration").dxButton({
        icon: "edit",
        width: "25%",
        disabled: false,
        onClick: function(e) { 
            $("#popup-editconfiguration").dxPopup("show");
        },
    });

    // Optionen der Eingabetextboxen
    var inputTextBoxOptions = {
        // 'value' muss definiert sein, sonst ist ein gelöschter Wert valide
        value: "1",
        maskInvalidMessage: "Unzulässiger Wert",
        showClearButton: true,
        onChange: function(e) {
            var isAllValid = true;

            try {
                result = eval(e.component.option("value"));
                if (typeof(result) == "undefined") {
                    e.component.option("isValid", false);
                };
            }
            catch (error) {
                e.component.focus();
                e.component.option("isValid", false);
                DevExpress.ui.notify("Keine auswertbare Anweisung", "error");
            };

            for (var i=0; i<3; i++) {
                isAllValid = $("#textbox-key"+i).dxTextBox('instance').option("isValid");
                if (!isAllValid) break;
            }
            $("#button-saveconfiguration").dxButton("instance").option("disabled", !isAllValid);
        },
    };
    
    var editConfigurationPopup = $("#popup-editconfiguration").dxPopup({
        showTitle: true,
        showCloseButton: true,
        dragEnabled: false,
        closeOnOutsideClick: true,
        onShown: function (e) {
            e.component.option("title", "Konfiguration '" + configurationSelectBox.option("value") + "'");
            $("#textbox-key0").dxTextBox($.extend(true, {}, inputTextBoxOptions, {
                mask: "x",
                maskRules: {"x": /[12]/}
            }));
            $("#textbox-key1").dxTextBox($.extend(true, {}, inputTextBoxOptions, {
                mask: "xxx",
                maskRules: {"x": /[0-9]/}
            }));
            $("#textbox-key2").dxTextBox($.extend(true, {}, inputTextBoxOptions, {
                mask: "xxxxxxxxxxxxxxxxxxxx",
                maskRules: {"x": /[0-9 +-/*]/},
            }));
            WebSocket_Send('getConfig');
            $("#button-saveconfiguration").dxButton($.extend(true, {}, metalButtonOptions, {
                icon: "fas fa-save",
                elementAttr: {
                    style: "color: var(--tm-green)",
                },
                onClick: function(e) {
                    var writeConfig = '';
                    for (var i=0; i<3; i++) {
                        writeConfig += document.getElementById("label-key"+i).innerHTML + "=" +
                        $("#textbox-key"+i).dxTextBox('instance').option("value") + "&";
                    }
                    // letztes '&' löschen
                    writeConfig = writeConfig.substr(0, writeConfig.length-1);
                    WebSocket_Send('writeConfig:' + writeConfig);
                    editConfigurationPopup.hide();
                },
            }));
            
            $("#button-resetconfiguration").dxButton($.extend(true, {}, metalButtonOptions, {
                icon: "fas fa-undo-alt",
                elementAttr: {
                    style: "color: var(--tm-blue)",
                },
                disabled: false,
                onClick: function(e) {
                    WebSocket_Send('getConfig');
                    $("#button-saveconfiguration").dxButton("instance").option("disabled", true);
                },
            }));
        },
    }).dxPopup("instance");

    var stageTextbox = $("#textbox-stage").dxTextBox($.extend(true, {}, textBoxOptions,{
    })).dxTextBox("instance");
    
    var totalTextbox = $("#textbox-total").dxTextBox($.extend(true, {}, textBoxOptions,{
    })).dxTextBox("instance");

});
