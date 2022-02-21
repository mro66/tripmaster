var audioWineGlass = document.createElement('audio');
audioWineGlass.setAttribute('src', '/static/Wine_Glass.ogg');
var countdownRunning = false;


// Array [] von Objekten {}
// !!! MUSS MIT POINTS DICTIONARY IN tripmaster_web.py ÜBEREINSTIMMEN !!!
var pointList = [{
    Variable: "checkpoint:null",
    Name: "Inaktiv",
}, {
    Name: "Zählpunkte",
    "expanded": true,
    items: [{
        Variable: "countpoint:roundabout",
        Name: "Kreisverkehr",
    }, {
        Variable: "countpoint:countpoint",
        Name: "Sonstiges",
    }],
}, {
    Name: "Orientierungskontrollen",
    "expanded": true,
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

// Extrahiert die Orientierungskontrollen aus der pointList als Array
function getCheckpointList() {
    let cpl = [];
    for (i = 0; i < pointList.length; i++) {
        if (pointList[i].Name == "Orientierungskontrollen") {
            for (j = 0; j < pointList[i].items.length; j++) {
              cpl.push(pointList[i].items[j].Name);
            };
        };
    };
    return cpl;
};

// Zahlenfeld mit <<, <, >, >>
var numberBoxOptions = {
    inputAttr: {
        style: "font-size: 7vmin; text-align: center",
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

// Datumsfelder für Etappenstart und -ende
var dateBoxOptions = {
    placeholder: "00:00",
    showClearButton: true,
    displayFormat: "HH:mm",
    pickerType: "rollers",
    type: "time",
    openOnFieldClick: true,
    showDropDownButton: false,
    onValueChanged: function(e) {
        let value = e.component.option("value");
        if (value != null) {
            value.setSeconds(0)
            value.setMilliseconds(0);
            value = value.getTime();
        } else {
            document.getElementById("label-stagetimeto").innerHTML = "Verbleibende Zeit";
        };
        if (e.element.attr("id") == "datebox-stagestart") {
            if (!stageStarted.status) {
                WebSocket_Send("setStageStart:"+value);
            }
        } else if (e.element.attr("id") == "datebox-stagefinish") {
            WebSocket_Send("setStageFinish:"+value);
        };
    },
};

var jumpToLastPage = false; 

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
            // GLP
            "title": [],
            icon: "fas fa-stopwatch",
            template: $("#tab-regtest"),
        }, {
            // Settings
            "title": [],
            icon: "fas fa-cogs",
            template: $("#tab-setup"),
        }],
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
                        setSectorPreset(-1);
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        setSectorPreset(-.05);
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        setSectorPreset(.05);
                    },
                },
            },
            {
                options: {
                    onClick: function(e) {
                        setSectorPreset(1);
                    },
                },
            },
        ],
    })).dxNumberBox("instance");

        function setSectorPreset(diff) {
            let newval = parseFloat(sectorPresetNumberBox.option("value")) + diff;
            if (newval < sectorPresetNumberBox.option("step")) {
                sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("min"));
            } else if (newval > sectorPresetNumberBox.option("max")) {
                sectorPresetNumberBox.option("value", sectorPresetNumberBox.option("max"));
            } else {
                sectorPresetNumberBox.option("value", newval);
            };
        };
        
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
            // sectorTextBox.option("value", formatDistance(0));
            sectorPresetTextBox.option("value", "0 m");
            sectorPresetRestTextBox.option("value", "0 m");
            // Wenn der Abschnitt zurückgesetzt wird, fahren wir vorwärts
            if (reverseButton.option("icon") === "fas fa-arrow-down") {
                setReverse(false);
            }
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
            if (REVERSE) {
                e.component.option("icon", "fas fa-arrow-down");
                e.component.option("elementAttr", {"style": "color: var(--tm-red)"});
            } else {
                e.component.option("icon", "fas fa-arrow-up");
                e.component.option("elementAttr", {"style": "color: var(--tm-green)"});
            }                
        },
        onClick: function(e) {
            setReverse(e.component.option("icon") === "fas fa-arrow-up");
        },
    })).dxButton("instance");
    
        function setReverse(backwards) {
            if (backwards) {
                WebSocket_Send("reverse:true");
                reverseButton.option("icon", "fas fa-arrow-down");
                reverseButton.option("elementAttr", {"style": "color: var(--tm-red)"});
                // Wenn rückwärts, dann roter Text
                $("#textbox-sector").find(".dx-texteditor-input").css("color", "var(--tm-red)");                    
            } else {
                WebSocket_Send("reverse:false");
                reverseButton.option("icon", "fas fa-arrow-up");
                reverseButton.option("elementAttr", {"style": "color: var(--tm-green)"});
                $("#textbox-sector").find(".dx-texteditor-input").css("color", "");                    
            };          
        };
    
    // Anzeige km-Stand Abschnitt
    var sectorTextBox = $("#textbox-sector").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: formatDistance(0),
        onContentReady: function(e) {
            if (REVERSE) {
                // Wenn rückwärts, dann roter Text
                $("#textbox-sector").find(".dx-texteditor-input").css("color", "var(--tm-red)");                    
            } else {
                $("#textbox-sector").find(".dx-texteditor-input").css("color", ""); 
            }                
        },
    })).dxTextBox("instance");

    var sectorPresetTextBox = $("#textbox-sectorpreset").dxTextBox($.extend(true, {}, textBoxOptions,{
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

    var sectorPresetRestTextBox = $("#textbox-sectorpresetrest").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
    })).dxTextBox("instance");

    // Startzeit Etappe
    $("#datebox-stagestart").dxDateBox($.extend(true, {}, dateBoxOptions,{
    }));

    // Zielzeit Etappe
    $("#datebox-stagefinish").dxDateBox($.extend(true, {}, dateBoxOptions,{
    }));

    $("#textbox-stagetimeto").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "--:--:--",
    }));

    // Anzeige km-Stand Etappe
    $("#textbox-stage").dxTextBox($.extend(true, {}, textBoxOptions,{
    }));
    
    // Anzeige km-Stand Rallye
    $("#textbox-rallye").dxTextBox($.extend(true, {}, textBoxOptions,{
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
                dataField: "Name",
                allowEditing: true,
                lookup: {
                    dataSource: getCheckpointList(),
                }
            },
            {
                dataField: "Wert",
                allowEditing: true,
                width: "19vmin",
                alignment: "center",
            },
            {
                dataField: "Aktiv",
                dataType: "boolean",
                caption: "Akt.",  
                width: "15vmin",
            },
        ],
        onRowUpdated: function(e) {
            // ID zur Anzeige 1-basiert, im System 0-basiert
            id = e.data.ID - 1;
            name = e.data.Name;
            // Schreibt jeden Klein- in Großbuchstaben um
            e.data.Wert = e.data.Wert.toUpperCase();
            value = e.data.Wert;
            active = e.data.Aktiv;           
            WebSocket_Send("changepoint:checkpoint&"+id+"&"+name+"&"+value+"&"+(active?1:0));
        },
        onContentReady: function(e){
            if (jumpToLastPage) {  
                jumpToLastPage = false;  
                let totalCount = e.component.totalCount(); 
                let pageSize = e.component.pageSize();  
                let pageCount = Math.floor(totalCount / pageSize);  
                if (pageCount && totalCount % pageSize) {  
                    e.component.pageIndex(pageCount);  
                }  
            }
        },
    }));

// Tab GLP

    // Start und Reset Buttons
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
                WebSocket_Send('startRegtest:'+ parseInt(regtestTimeNumberBox.option("value")) + '&' 
                                              + parseFloat(regtestDistanceNumberBox.option("value")) + '&' 
                                              + parseFloat(regtestSpeedNumberBox.option("value")));
                countdownRunning = true;
                // Stopzeichen
                e.component.option("icon", "far fa-times-circle");
                e.component.option("elementAttr", {"style": "color: var(--tm-red)"});
                resetRegtestButton.option("disabled", true);
                $("#textbox-regtesttime").find(".dx-texteditor-input").css("color", "var(--tm-red)");
            } else {
                WebSocket_Send('stopRegtest');
                resetRegtest();
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
            resetRegtest();
        },
    })).dxButton("instance"); 

        function resetRegtest(flicker = false) {
            countdownRunning = false;
            setRegtestButton.option("icon", "fas fa-check");
            setRegtestButton.option("elementAttr", {"style": "color: var(--tm-green)"});
            setRegtestButton.option("disabled", true);
            resetRegtestButton.option("disabled", true);
           // reset regtestStartTimeNumberBox
            resetRegtestNumberBox(regtestTimeNumberBox);
            resetRegtestNumberBox(regtestDistanceNumberBox);
            resetRegtestNumberBox(regtestSpeedNumberBox);
            
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
    var regtestTimeNumberBox = $("#numberbox-regtesttime").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 1200,
        step: 1,
        format: "#0 sek",
        onValueChanged: function (e) {
            regtestTimeTextBox.option("value", formatTime(e.value));
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        calcRegtest(regtestTimeNumberBox, -20);
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        calcRegtest(regtestTimeNumberBox, -1);
                    },
                }
            },
            {
                options: {
                   onClick: function(e) {
                        calcRegtest(regtestTimeNumberBox, 1);
                    },
                  }
            },
            {
                options: {
                    onClick: function(e) {
                        calcRegtest(regtestTimeNumberBox, 20);
                    }
                }
            }
        ],
    })).dxNumberBox("instance");

    // Streckenvorgabe
    var regtestDistanceNumberBox = $("#numberbox-regtestdistance").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 25,
        step: 0.05,
        format: "#0.00 km",
        onValueChanged: function(e) {
            regtestDistanceTextBox.option("value", formatDistance(e.value));
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        calcRegtest(regtestDistanceNumberBox, -1);
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        calcRegtest(regtestDistanceNumberBox, -.05);
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        calcRegtest(regtestDistanceNumberBox, .05);
                    },
                },
            },
            {
                options: {
                    onClick: function(e) {
                        calcRegtest(regtestDistanceNumberBox, 1);
                    },
                },
            },
        ],
    })).dxNumberBox("instance");
      
    // Geschwindigkeitsvorgabe
    var regtestSpeedNumberBox = $("#numberbox-regtestspeed").dxNumberBox($.extend(true, {}, numberBoxOptions, {
        max: 80,
        step: 0.1,
        format: "#0.0 km/h",
        onValueChanged: function(e) {
            regtestSpeedTextBox.option("value", formatSpeed(e.value));
        },
        buttons: [
            {
                options: {
                    onClick: function(e) {
                        calcRegtest(regtestSpeedNumberBox, -2);
                   },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        calcRegtest(regtestSpeedNumberBox, -.1);
                    },
                },
            },
            {
                options: {
                   onClick: function(e) {
                        calcRegtest(regtestSpeedNumberBox, .1);
                    },
                },
            },
            {
                options: {
                    onClick: function(e) {
                        calcRegtest(regtestSpeedNumberBox, 2);
                    },
                },
            },
        ],
    })).dxNumberBox("instance");
      
    function resetRegtestNumberBox(numberbox, newval = 0) {
        numberbox.option("value", newval);
        numberbox.option("disabled", (newval != 0));                        
    }
        
    // (A) Setzen des Wertes einer Numberbox über die Buttons, (B) Definition der GLP aus Zeit-, Strecken- und/oder Geschwindigkeitsvorgabe
    function calcRegtest(numberbox, diff) {
        let oldval = Number.isInteger(numberbox.option("step"))?parseInt(numberbox.option("value")):parseFloat(numberbox.option("value"))
        let newval = oldval + diff;
        if (newval < numberbox.option("step")) {
            numberbox.option("value", numberbox.option("min"));
        } else if (newval > numberbox.option("max")) {
            numberbox.option("value", numberbox.option("max"));
        } else {
            numberbox.option("value", newval);
        };

        // wenn ein Feld disabled ist, wird sein Wert auf 0 gesetzt
        let time     = !regtestTimeNumberBox.option("disabled")     * parseInt(regtestTimeNumberBox.option("value"));
        let distance = !regtestDistanceNumberBox.option("disabled") * parseFloat(regtestDistanceNumberBox.option("value"));
        let speed    = !regtestSpeedNumberBox.option("disabled")    * parseFloat(regtestSpeedNumberBox.option("value"));
        
        // wenn mindestens ein Feld > 0 ist, dann kann das Formular zurückgesetzt werden
        if (time + distance + speed == 0) {
            resetRegtestButton.option("disabled", true);
            setRegtestButton.option("disabled", true);
        } else {
            // wenn zwei Felder > 0 sind, dann drittes Feld berechnen
            resetRegtestButton.option("disabled", false);
            // keine Geschwindigkeitsvorgabe: aus Strecke und Zeit berechnen
            if ((distance > 0) && (time > 0)) {
                resetRegtestNumberBox(regtestSpeedNumberBox, distance / time * 3600);                  
                setRegtestButton.option("disabled", !stageStarted.status);
            // keine Zeitvorgabe: aus Strecke und Geschwindigkeit berechnen
            } else if ((distance > 0) && (speed > 0 )) {
                resetRegtestNumberBox(regtestTimeNumberBox, distance / speed * 3600);
                setRegtestButton.option("disabled", !stageStarted.status);
            // keine Streckenvorgabe: aus Zeit und Geschwindigkeit berechnen
            } else if ((time > 0) && (speed > 0)) {
                resetRegtestNumberBox(regtestDistanceNumberBox, time * speed / 3600);
                setRegtestButton.option("disabled", !stageStarted.status);
            // Wenn nur ein Feld > 0 ist, dann die beiden anderen auf 0 setzen
            } else if ((distance > 0) && (time == 0) && (speed == 0)) {
                resetRegtestNumberBox(regtestTimeNumberBox);
                resetRegtestNumberBox(regtestSpeedNumberBox);
                setRegtestButton.option("disabled", true);
            }  else if ((distance == 0) && (time > 0) && (speed == 0)) {
                resetRegtestNumberBox(regtestDistanceNumberBox);
                resetRegtestNumberBox(regtestSpeedNumberBox);
                setRegtestButton.option("disabled", true);
            }  else if ((distance == 0) && (time == 0) && (speed > 0)) {
                resetRegtestNumberBox(regtestDistanceNumberBox);
                resetRegtestNumberBox(regtestTimeNumberBox);
                setRegtestButton.option("disabled", true);
            }                        
        }
    };

    /* Startzeit (TODO: nicht fertig implementiert)
    
    var regtestStartHourNumberBox = $("#numberbox-regteststarthour").dxNumberBox({
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
        
    var regtestStartMinuteNumberBox = $("#numberbox-regteststartminute").dxNumberBox({
        min: -1, max: 60,
        value: 0,
        step: 1,
        format: "#0 min",
        showSpinButtons: true,
        useLargeSpinButtons: false,
        onValueChanged: function (e) {
            if (e.value == e.component.option("max")) {
                e.component.option("value", 0);
                regtestStartHourNumberBox.option("value", regtestStartHourNumberBox.option("value")+1);
            } else if (e.value == e.component.option("min")) {
                e.component.option("value", e.component.option("max")-e.component.option("step"));
                regtestStartHourNumberBox.option("value", regtestStartHourNumberBox.option("value")-1);
            } else if (e.value == null) {
                e.component.option("value", 0);
            }                    
            setRegtestStartTime();
        },
    }).dxNumberBox("instance");
        
    var regtestStartSecondNumberBox = $("#numberbox-regteststartsecond").dxNumberBox({
        min: -1, max: 60,
        value: 0,
        step: 1,
        format: "#0 s",
        showSpinButtons: true,
        useLargeSpinButtons: false,
        onValueChanged: function (e) {
            if (e.value == e.component.option("max")) {
                e.component.option("value", 0);
                regtestStartMinuteNumberBox.option("value", regtestStartMinuteNumberBox.option("value")+1);
            } else if (e.value == e.component.option("min")) {
                e.component.option("value", e.component.option("max")-e.component.option("step"));
                regtestStartMinuteNumberBox.option("value", regtestStartMinuteNumberBox.option("value")-1);
            } else if (e.value == null) {
                e.component.option("value", 0);
            }                    
            setRegtestStartTime();
        },        
    }).dxNumberBox("instance");

    function getRegtestStartTime() {
        var startHour = regtestStartHourNumberBox.option("value");
        var startMinute = regtestStartMinuteNumberBox.option("value");
        var startSecond = regtestStartSecondNumberBox.option("value");
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
    var regtestTimeTextBox = $("#textbox-regtesttime").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 sek",
        onValueChanged: function(e) {
            var countdownText = document.getElementById("textbox-regtesttime").children[0].children[0].children[0];
            var time = parseInt(e.value);
            regtestMinutesDecimalTextBox.option("value", formatNumber(time/60) + " min");
            let sek = "0" + time % 60;
            regtestMinutesTextBox.option("value", parseInt(time/60) + ":" + sek.substr(sek.length - 2) + " min");
            if (countdownRunning == true) {
                if (time > 0) {
                    regtestDistanceTextBox.option("value", formatDistance(KM_SECTOR_PRESET_REST));
                    animationClass = "secondyellow";
                    countdownText.style.color = "var(--tm-red)";
                    if (time <= 10) {
                        if (time <= 5) {
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
                    resetRegtest(true);
                    setTimeout(function() {
                            resetSectorPreset();
                            WebSocket_Send('resetSector');
                        }, 2000);
                }
            };
        },
    })).dxTextBox("instance");
    
    var regtestMinutesTextBox = $("#textbox-regtestminutes").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0:00 min",
    })).dxTextBox("instance");
    
    var regtestMinutesDecimalTextBox = $("#textbox-regtestminutesdecimal").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0,00 min",
    })).dxTextBox("instance");
    
    var regtestDistanceTextBox = $("#textbox-regtestdistance").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 m",
    })).dxTextBox("instance");
            
    var regtestSpeedTextBox = $("#textbox-regtestspeed").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: formatSpeed(0),
    })).dxTextBox("instance");
    
// Tab Zählpunkte

   $("#datagrid-countpoint").dxDataGrid($.extend(true, {}, dataGridOptions, {
        columns: [
            {
                dataField: "ID",
                allowEditing: false,
                width: "11vmin",
            },
            {
                dataField: "Name",
                allowEditing: false,
            },
            {
                dataField: "Aktiv",
                dataType: "boolean",
                caption: "Akt.",
                width: "15vmin",
            },
        ],
        summary: {
            totalItems: [
                {
                    column: "Aktiv",
                    summaryType: "sum",
                    showInColumn: "Name",
                }
            ],
            texts: {
                sumOtherColumn: "Anzahl: {0}"
            }
        },
        onRowUpdated: function(e) {
            // ID zur Anzeige 1-basiert, im System 0-basiert
            id = e.data.ID - 1;
            name = e.data.Name;
            value = e.data.Wert;
            active = e.data.Aktiv;
            WebSocket_Send("changepoint:countpoint&"+id+"&"+name+"&"+value+"&"+(active?1:0));
        },
    }));

// Tab Setup

	// Rallye
	
    // Neu starten
    $("#button-newrallye").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-asterisk",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onClick: function(e) {
            confirmDialog("Neue Rallye starten").show().done(function (dialogResult) {
                if (dialogResult) {
                    WebSocket_Send('newRallye');
                    location.reload();
                }
            });
        },
    })); 

	// KMZ herunterladen
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
        showCloseButton: false,
        dragEnabled: false,
        closeOnOutsideClick: false,
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
                loadPanel: {
                	enabled: "auto",
                	text: "Lade Dateien...",
                	showIndicator: true,
            	},
                onInitialized: function(e) {
                    e.component.beginCustomLoading();
                    WebSocket_Send("getFiles");
                },
                onRowRemoving: function(e) {
                    filename = e.data.Dateiname;
                    WebSocket_Send("deleteFile:" + filename);
                },
            }));
        },
        onHidden: function(e) {
	        e.component.option("showCloseButton", false);
            $("#datagrid-files").dxDataGrid("dispose");
        },
    });

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

    
    // Tripmaster

	// Sound ein/aus
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

	// Tornado im DEBUG-Modus neustarten
    $("#button-startdebug").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-bug",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-green)",
        },
        onClick: function(e) {
            confirmDialog("Neustart Server DEBUG").show().done(function (dialogResult) {
                if (dialogResult) {
		            document.getElementById("reloadpage").style.display = "flex";
		            document.getElementsByName("main")[0].style.display = "none";
                    WebSocket_Send('startDebug');
                    setTimeout(function() {
                        location.reload();
                    }, 20000);                        
                }
            });
        },
    })); 

	// Tornado neustarten
    $("#button-startnew").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-redo",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
            confirmDialog("Neustart Server").show().done(function (dialogResult) {
                if (dialogResult) {
		            document.getElementById("reloadpage").style.display = "flex";
		            document.getElementsByName("main")[0].style.display = "none";
                    WebSocket_Send('startNew');
                    setTimeout(function() {
                        location.reload();
                    }, 20000);                        
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
        width: "23%",
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
        onInput: function(e) {
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

            for (var i=0; i<2; i++) {
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
            // Radumfang
            $("#textbox-key0").dxTextBox($.extend(true, {}, inputTextBoxOptions, {
                mask: "xxx",
                maskRules: {"x": /[0-9]/}
            }));
            // Übersetzung
            $("#textbox-key1").dxTextBox($.extend(true, {}, inputTextBoxOptions, {
                mask: "xxxxxxxxxxxxxxxxxxxx",
                maskRules: {"x": /[0-9 + - / *]/},
            }));
            WebSocket_Send('getConfig');
            $("#button-saveconfiguration").dxButton($.extend(true, {}, metalButtonOptions, {
                icon: "fas fa-save",
                elementAttr: {
                    style: "color: var(--tm-green)",
                },
                onClick: function(e) {
                    var writeConfig = '';
                    for (var i=0; i<2; i++) {
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
    
    // RasPi
    
    // Herunterfahren
    $("#button-sudohalt").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-power-off",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-red)",
        },
        onClick: function(e) {
            confirmDialog("RasPi herunterfahren").show().done(function (dialogResult) {
                if (dialogResult) {
		            document.getElementById("reloadpage").style.display = "flex";
		            document.getElementsByName("main")[0].style.display = "none";
                    WebSocket_Send('sudoHalt');
                }
            });
        },
    })); 

	// Neu starten
    $("#button-sudoreboot").dxButton($.extend(true, {}, metalButtonOptions, {
        icon: "fas fa-redo",
        disabled: false,
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
            confirmDialog("RasPi neu starten").show().done(function (dialogResult) {
                if (dialogResult) {
		            document.getElementById("reloadpage").style.display = "flex";
		            document.getElementsByName("main")[0].style.display = "none";
                    WebSocket_Send('sudoReboot');
                }
            });
        },
    })); 
    
    // Anzeige Akkuspannung
    $("#textbox-ubat").dxTextBox($.extend(true, {}, textBoxOptions,{
    }));

    // Anzeige CPU Temperatur
    $("#textbox-cputemp").dxTextBox($.extend(true, {}, textBoxOptions,{
    }));

    // Anzeige CPU Last
    $("#textbox-cpuload").dxTextBox($.extend(true, {}, textBoxOptions,{
    }));

    // Anzeige GPS Signal
    $("#textbox-gps").dxTextBox($.extend(true, {}, textBoxOptions,{
    }));

    // Anzeige Uhrzeit
    $("#textbox-clock").dxTextBox($.extend(true, {}, textBoxOptions,{
    }));

});
