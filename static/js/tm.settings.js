var audioWineGlass = document.createElement('audio');
audioWineGlass.setAttribute('src', '/static/Wine_Glass.ogg');
var countdownRunning = false;

var pointList = [{
    Variable: "checkpoint:null",
    Name: "Inaktiv",
}, {
    Name: "Zählpunkte",
    items: [{
        Variable: "countpoint:roundabout",
        Name: "Kreisverkehr",
    }, {
        Variable: "countpoint:countpoint",
        Name: "Sonstiges",
    }],
}, {
    Name: "Orientierungskontrollen",
    items: [{
        Variable: "checkpoint:roundabout",
        Name: "Kreisverkehr",
    }, {
        Variable: "checkpoint:townsign",
        Name: "Ortsschild",
    }, {
        Variable: "checkpoint:stampcheck",
        Name: "Stempelkontrolle",
    }, {
        Variable: "checkpoint:mutecheck",
        Name: "Stummer Wächter",
    }, {
        Variable: "checkpoint:checkpoint",
        Name: "Sonstige OK",
    }]
}];

var checkpointList = ["Kreisverkehr", "Ortsschild", "Stempelkontrolle", "Stummer Wächter", "Sonstige OK"];

// Zahlenfeld mit <<, <, >, >>
var numberBoxOptions = {
    inputAttr: {
        style: "font-size: 7.1vmin; text-align: center",
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
        style: "font-size: 5.3vmin",
    },
    dataSource: [
    ],
    sorting: {
        mode: "None",
    },
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
        pageSize: 10,
    },
}

var pointButtonOptions = {
    disabled: false,
    onClick: function(e) {
        // Übergabe der ID des Button Elements (z. B. "button-1") an das Popup
        $("#popup-setbutton").dxPopup("instance").option("elementAttr", {"name": e.component.element().attr("id")});
        $("#popup-setbutton").dxPopup("show");
    },
};


$(function(){

// TabPanel 

     $("#tabpanel-settings").dxTabPanel({
        deferRendering: false,
        height: "100%",
        loop: true,
        selectedIndex: 0,
        items: [{
            // Strecke
            "title": [],
            icon: "fas fa-route",
            template: $("#tab-sector"),
        }, {
            // GLP
            "title": [],
            icon: "fas fa-stopwatch",
            template: $("#tab-regtest"),
        }, {
            // Zählpunkte
            title: [],
            icon: "fas fa-hashtag",
            template: $("#tab-countpoint"),
        }, {
            // Orientierungskontrollen
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
            } else if (e.component.option("selectedIndex")==4) {
                $("#textbox-sector").appendTo("#tab4_sector");
            }
        }
    });

// Tab Abschnitt

    var sectorPresetNumberBox = $("#numberbox-sectorpreset").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 25,
        step: 0.05,
        format: "#0.00 km",
        onValueChanged: function(e) {
            $("#button-setsector").dxButton("instance").option("disabled", (e.value === 0.0) || !stageStarted.status);
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
                        };
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
                        };
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = sectorPresetNumberBox.option("value") + .05;
                        if (newval >= sectorPresetNumberBox.option("max")) {
                            sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("max"));
                        } else {
                            sectorPresetNumberBox.option("value", newval);
                        };
                    },
                },
            },
            {
                options: {
                    onClick: function(e) {
                        let newval = sectorPresetNumberBox.option("value") + 1;
                        if (newval >= sectorPresetNumberBox.option("max")) {
                            sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("max"));
                        } else {
                            sectorPresetNumberBox.option("value", newval);
                        };
                    },
                },
            },
        ],
    })).dxNumberBox("instance");

    $("#button-setsector").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-check",
        disabled: true,
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onClick: function(e) {
            let sectorLength = parseFloat(sectorPresetNumberBox.option("value"));
            setReverse(false);
            WebSocket_Send('setSectorLength:'+sectorLength);
            sectorPresetNumberBox.option("value", 0);
        },
    })) 

    $("#button-resetsectorpreset").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-undo-alt",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            resetSectorPreset();
        },
    })); 

        function resetSectorPreset() {
            sectorPresetNumberBox.option("value", 0);
            // sectorTextbox.option("value", formatDistance(0));
            sectorPresetTextbox.option("value", "0 m");
            sectorPresetRestTextbox.option("value", "0 m");
            setReverse(false);
            if (stageStarted.status)
                WebSocket_Send('setSectorLength:0.0');
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
    
    // Anzeige der km-Stände
    var sectorTextbox = $("#textbox-sector").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: formatDistance(0),
    })).dxTextBox("instance");

    var sectorPresetTextbox = $("#textbox-sectorpreset").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
        onValueChanged: function(e) {
            if (isSoundEnabled()) {
                if ((unformatDistance(e.value) == 0) && (unformatDistance(e.previousValue) > 0)) {
                    // Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
                    audioWineGlass.play().catch(function(error) { });
                }
            }
        }
    })).dxTextBox("instance");

    var sectorPresetRestTextbox = $("#textbox-sectorpresetrest").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
    })).dxTextBox("instance");

    // Startzeit Etappe
    $("#datebox-stagestart").dxDateBox({
        placeholder: "00:00",
        showClearButton: true,
        displayFormat: "HH:mm",
        pickerType: "rollers",
        type: "time",
        // value: new Date(),
        openOnFieldClick: true,
        showDropDownButton: false,
        onValueChanged: function(e) {
            let stagestart = e.component.option("value");
            if (stagestart != null) {
                stagestart.setSeconds(0)
                stagestart.setMilliseconds(0);
                stagestart = stagestart.getTime();
            } else {
                document.getElementById("label-stagetimeto").innerHTML = "Verbleibende Zeit";
            }
            WebSocket_Send("setStageStart:"+stagestart)
        },
    });

    // Zielzeit Etappe
    $("#datebox-stagefinish").dxDateBox({
        placeholder: "00:00",
        showClearButton: true,
        displayFormat: "HH:mm",
        pickerType: "rollers",
        type: "time",
        // value: new Date(),
        openOnFieldClick: true,
        showDropDownButton: false,
        onValueChanged: function(e) {
            let stagefinish = e.component.option("value");
            if (stagefinish != null) {
                stagefinish.setSeconds(0)
                stagefinish.setMilliseconds(0);
                stagefinish = stagefinish.getTime();
            } else {
                document.getElementById("label-stagetimeto").innerHTML = "Verbleibende Zeit";
            }
            WebSocket_Send("setStageFinish:"+stagefinish)
        },
    });

    $("#textbox-stagetimeto").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "--:--:--",
    }));

// Tab GLP

    var setRegtestButton = $("#button-setregtest").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-check",
        disabled: true,
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onClick: function(e) {
            if (countdownRunning == false) {
                resetSectorPreset();
                WebSocket_Send('resetSector');
                WebSocket_Send('startRegtest:'+getRegtestTime());
                if (getRegtestLength() > 0) {
                    WebSocket_Send('setRegtestLength:'+getRegtestLength());                        
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
                setTimeout(function() {
                        resetSectorPreset();
                        WebSocket_Send('resetSector');
                    }, 2000);
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
                if (stageStarted.status)
                    setRegtestButton.option("disabled", false);
                // setRegtestStartTime();
            } else {
                resetRegtestButton.option("disabled", true);
                setRegtestButton.option("disabled", true);
            }
            setRegtestAvgSpeed();
        };
   
    // Streckenvorgabe
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

    // Geschwindigkeitsvorgabe
    var regtestAvgSpeedNumberBox = $("#numberbox-regtestavgspeed").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 80,
        step: 0.1,
        format: "#0.0 km/h",
        onValueChanged: function(e) {
            // setRegtestLength();
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        let newval = regtestAvgSpeedNumberBox.option("value") - 2;
                        if (newval <= regtestAvgSpeedNumberBox.option("min")) {
                            regtestAvgSpeedNumberBox.option("value", regtestAvgSpeedNumberBox.option("min"));
                        } else {
                            regtestAvgSpeedNumberBox.option("value", newval);
                        }
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = regtestAvgSpeedNumberBox.option("value") - .1;
                        if (newval <= regtestAvgSpeedNumberBox.option("min")) {
                            regtestAvgSpeedNumberBox.option("value", regtestAvgSpeedNumberBox.option("min"));
                        } else {
                            regtestAvgSpeedNumberBox.option("value", newval);
                        }
                    },
                }
            },
            {
                options: {
                   onClick: function(e) {
                        let newval = regtestAvgSpeedNumberBox.option("value") + .1;
                        if (newval >= regtestAvgSpeedNumberBox.option("max")) {
                            regtestAvgSpeedNumberBox.option("value", regtestAvgSpeedNumberBox.option("max"));
                        } else {
                            regtestAvgSpeedNumberBox.option("value", newval);
                        }
                    },
                  }
            },
            {
                options: {
                    onClick: function(e) {
                        let newval = regtestAvgSpeedNumberBox.option("value") + 2;
                        if (newval >= regtestAvgSpeedNumberBox.option("max")) {
                            regtestAvgSpeedNumberBox.option("value", regtestAvgSpeedNumberBox.option("max"));
                        } else {
                            regtestAvgSpeedNumberBox.option("value", newval);
                        }
                    }
                }
            }
        ],
    })).dxNumberBox("instance");
      

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
                        audioWineGlass.play().catch(function(error) { });
                    };
                    resetRegtest();
                    setTimeout(function() {
                            resetSectorPreset();
                            WebSocket_Send('resetSector');
                        }, 2000);
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
                width: "11vmin",
            },
            {
                dataField: "Beschreibung",
                allowEditing: false,
            },
            {
                dataField: "Sicher",
                dataType: "boolean",
                caption: "OK",
                width: "15vmin",
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

// Tab Orientierungskontrollen

    $("#datagrid-checkpoint").dxDataGrid($.extend(true, {}, dataGridOptions, {
        columns: [
            {
                dataField: "ID",
                allowEditing: false,
                width: "11vmin",
            },
            {
                dataField: "Beschreibung",
                allowEditing: true,
                lookup: {
                    dataSource: checkpointList,
                }
            },
            {
                dataField: "Name",
                allowEditing: true,
                width: "21vmin",
            },
            {
                dataField: "Sicher",
                dataType: "boolean",
                caption: "OK",  
                width: "15vmin",
            },
        ],
        onRowUpdated: function(e) {
            id = e.data.ID;
            description = e.data.Beschreibung;
            // Schreibt jeden Klein- in Großbuchstaben um
            e.data.Name = e.data.Name.toUpperCase();
            name = e.data.Name;
            visibility = e.data.Sicher;           
            WebSocket_Send("changepoint:checkpoint&"+id+"&"+description+"&"+name+"&"+(visibility?1:0));
        },
    }));

// Tab Setup

    // RasPi
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

    // Tripmaster
    $("#button-download").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-save",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
            $("#popup-download").dxPopup("show");
        },
    })); 
    
    $("#popup-download").dxPopup({
        showTitle: true,
        title: "Download",
        showCloseButton: true,
        dragEnabled: false,
        closeOnOutsideClick: true,
        height: "80%",
        deferRendering: false,
        onShown: function (e) {         
            $("#datagrid-files").dxDataGrid($.extend(true, {}, dataGridOptions, {
                columns: [
                    {
                        dataField: "Dateiname",
                        allowEditing: false,
                        cellTemplate: function (container, options) {
                            $("<div>")
                                .append($("<a>", { "href": "/out/"+options.value, "html": options.value }))
                                .appendTo(container);
                        }
                    },
                ],
                editing: {
                    mode: "row",
                    allowDeleting: true,
                    allowUpdating: false,
                    texts: {
                        confirmDeleteMessage: "Datei löschen?",
                    },
                    useIcons: true,
                },
                paging: {
                    pageSize: 8,
                },
                onInitialized: function(e) {
                    WebSocket_Send("getFiles");
                },
                onRowRemoving: function(e) {
                    filename = e.data.Dateiname;
                    mylog(filename);
                    WebSocket_Send("deleteFile:" + filename);
                },
            }));
        },
        onHidden: function(e) {
            $("#datagrid-files").dxDataGrid("dispose");
        },
    });

    $("#button-togglesound").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-volume-mute",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            if (isSoundEnabled()) {
                e.component.option("icon", "fas fa-volume-mute");
                e.component.option("elementAttr", {"style": "color: var(--tm-red)"});
            } else {
                e.component.option("icon", "fas fa-volume-up");
                e.component.option("elementAttr", {"style": "color: var(--tm-green)"});
                // Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
                audioWineGlass.play().catch(function(error) { });
            };
        },
    }));

        function isSoundEnabled() {
            return $("#button-togglesound").dxButton("instance").option("icon") === "fas fa-volume-up"
        };

    $("#button-resetrallye").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-redo",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
            confirmDialog("Reset Rallye").show().done(function (dialogResult) {
                if (dialogResult) {
                    WebSocket_Send('resetRallye');
                    // stageTextbox.option("value", formatDistance(0));
                    // rallyeTextbox.option("value", formatDistance(0));
                    location.reload();
                }
            });
        },
    })); 

    // Fahrzeugkonfiguration
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

    // Buttons
    $("#button-1").dxButton($.extend(true, {}, metalButtonOptions, pointButtonOptions, {
    })); 

    $("#button-2").dxButton($.extend(true, {}, metalButtonOptions, pointButtonOptions, {
    })); 

    $("#button-3").dxButton($.extend(true, {}, metalButtonOptions, pointButtonOptions, {
    })); 

    $("#button-4").dxButton($.extend(true, {}, metalButtonOptions, pointButtonOptions, {
    }));

    var setButtonPopup = $("#popup-setbutton").dxPopup({
        showTitle: true,
        title: "Buttondefinition",
        showCloseButton: true,
        dragEnabled: false,
        closeOnOutsideClick: true,
        height: "80%",
        deferRendering: false,
        onShown: function (e) {         
            $("#selectbox-checkpoint").dxTreeView({
                dataSource:  new DevExpress.data.DataSource({
                    store: pointList,
                }),
                displayExpr: "Name",
                valueExpr: "Variable",
                onContentReady: function(e) {
                    e.component.expandAll();
                },
                onItemClick: function(e) {
                    let settings = e.itemData.Variable;
                    if (typeof settings !== 'undefined') {
                        let id = setButtonPopup.element().attr("name");
                        WebSocket_Send(id +':' + settings);
                        setButtonPopup.hide();
                    }
                },
            });
        },
    }).dxPopup("instance");

    // Anzeige der km-Stände
    var stageTextbox = $("#textbox-stage").dxTextBox($.extend(true, {}, textBoxOptions,{
    })).dxTextBox("instance");
    
    var rallyeTextbox = $("#textbox-rallye").dxTextBox($.extend(true, {}, textBoxOptions,{
    })).dxTextBox("instance");

});
