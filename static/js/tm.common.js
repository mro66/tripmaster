var stageStart = {
    value: false,
    listener() {
        // Div Buttons der Settings (de)aktivieren
        if (document.getElementById("button-setsector") !== null) {
            let isZero = ($("#numberbox-sectorpreset").dxNumberBox("instance").option("value") == 0);
            $("#button-setsector").dxButton("instance").option("disabled", !this.value || isZero);
        };
        if (document.getElementById("button-setregtest") !== null) {
            let isZero = ($("#numberbox-regtesttime").dxNumberBox("instance").option("value") == 0);
            $("#button-setregtest").dxButton("instance").option("disabled", !this.value || isZero);
        };
        if (document.getElementById("button-download") !== null) {
            $("#button-download").dxButton("instance").option("disabled", this.value);
        };
        // Zählpunkte und Orientierungskontrollen aktivieren - nur Dashboard
        if (document.getElementById("multiview-dashboard") !== null) {
            for (let button = 1; button < 5; button++) {
                if (document.getElementById("button-"+button) !== null) {
                    $("#button-"+button).dxButton("instance").option("disabled", !this.value);
                };
            };
        };
    },
    get status() {
        return this.value;
    },
    set status(value) {
        if (value != this.value) {
            this.value = value;
            this.listener();
        };
    },
};

var kmLeftInSector = 0;
var kmSectorPreset = 0;

// Gemeinsame Optionen ...

// ... der Anzeigetextboxen
var textBoxOptions = {
    readOnly: true,
    focusStateEnabled: false,
    hoverStateEnabled: false,
};

// ... der Metallschaltflächen
var metalButtonOptions = {
    elementAttr: {
        class: "metal-button",
    },
    disabled: true,
    focusStateEnabled: false,
    hoverStateEnabled: false,
};
    
$(function(){

    // Reload nach Abbruch der WebSocket Verbindung    
    $("#button-reloadpage").dxButton($.extend(true, {}, metalButtonOptions, {
        disabled: false,
        icon: "fas fa-plug",
        width: "16vmax",
        height: "16vmax",
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
           location.reload();
         },
    }));   

    // Etappe Start/Stop
    $("#button-togglestage").dxButton($.extend(true, {}, metalButtonOptions, {
        onClick: function(e) {
            WebSocket_Send('toggleStage');
        },
    })); 


});

// Farbverlauf der Linearen Anzeige (leider deaktiviert, da bei einem Farbwechsel die Anzeige immer zuerst auf 0 springt :-(
    function setKmSector(fracSectorDriven) {
        fracSectorDriven = parseInt(fracSectorDriven);
        var colorConst = 153;
        var breakConst = 75;
        var redValue = colorConst;
        var greenValue = fracSectorDriven * colorConst / breakConst;
        if (fracSectorDriven > breakConst) {
            redValue = colorConst - (fracSectorDriven - breakConst) * colorConst / (100 - breakConst);
            greenValue = colorConst;
        };
        rgbColor = "rgb(" + redValue + "," + greenValue + ",0)";
        var subValues = [];
        if (fracSectorDriven > 0) {
            subValues = [fracSectorDriven];
        };
        var kmSectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge('instance');
        kmSectorLinearGauge.option({
            value: fracSectorDriven,
            valueIndicator: {
                color: "rgb(" + redValue + "," + greenValue + ",0)",
            },
            subvalues: subValues,
            subvalueIndicator: {
                color: "rgb(" + redValue + "," + greenValue + ",0)",
            },            
        });
    };

// Bestätigungsdialog

    function confirmDialog(dialogTitle) {
        return DevExpress.ui.dialog.custom({
            title: dialogTitle,
            messageHtml: "Bist Du sicher?",
            buttons: [
                { text: "Ja", onClick: function () { return true } },
                { text: "Nein", onClick: function () { return false } }
            ]
        });
    };
        
// Formatierung von Entfernungsangaben: unter 1 km in Metern, darüber in Kilometer mit zwei Nachkommastellen
    
    function formatDistance(distance) {
        if (Math.abs(distance) < 1) {
            return (distance * 1000) + " m";
        } else {
            return formatNumber(distance, 2) + " km";
        }
    };
    
// ... dasselbe rückgängig

    function unformatDistance(distance) {
        if (distance.includes(',')) {
            return parseFloat(distance.replace(",", "."));
        } else {
            return parseInt(distance) / 1000;
        }
    };

// Formatierung von Geschwindigkeitsangaben
    
    function formatSpeed(speed) {
        return formatNumber(speed, 1) + " km/h";
    };

// Formatierung von Zahlen mit standardmäßig zwei Nachkommastellen

    function formatNumber(value, digits=2) {
        return parseFloat(value).toLocaleString('de-DE', {minimumFractionDigits: digits, maximumFractionDigits: digits})
    }

// DEBUG

    function mynotify(msg) {
        DevExpress.ui.notify(msg, "info");
    };