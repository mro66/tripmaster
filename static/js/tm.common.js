DevExpress.localization.locale("de");
DevExpress.localization.loadMessages({
    de: { "Yes": "Ja", "No": "Nein", "Cancel": "Abbrechen" }
});

// Globale Variable
var kmLeftInSector = 0;
var kmSectorPreset = 0;
var stageStarted = {
    value: false,
    handler() {
        // Div Buttons der Settings (de)aktivieren
        if (document.getElementById("button-setsector") !== null) {
            let isZero = ($("#numberbox-sectorpreset").dxNumberBox("instance").option("value") == 0);
            $("#button-setsector").dxButton("instance").option("disabled", !this.value || isZero);
        };
        // if (document.getElementById("button-setregtest") !== null) {
            // let isZero = ($("#numberbox-regtesttime").dxNumberBox("instance").option("value") == 0);
            // $("#button-setregtest").dxButton("instance").option("disabled", !this.value || isZero);
        // };
        if (document.getElementById("button-download") !== null) {
            // $("#button-download").dxButton("instance").option("disabled", this.value);
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
            this.handler();
        };
    },
};

// Optionen Anzeigetextboxen
var textBoxOptions = {
    readOnly: true,
    focusStateEnabled: false,
    hoverStateEnabled: false,
};

// Optionen Metallbuttons
var metalButtonOptions = {
    elementAttr: {
        class: "metal-button",
    },
    disabled: true,
    focusStateEnabled: false,
    hoverStateEnabled: false,
};

// Optionen Etappe Start/Stop
var toggleStageButtonOptions = {
    icon: "fas fa-flag-checkered",
    elementAttr: {
        style: "color: var(--tm-gray)",
    },
    onClick: function(e) {
        audioClick.play().catch(function(error) { });
        if (stageStarted.status) {
            confirmDialog("Etappe beenden?").show().done(function (dialogResult) {
                if (dialogResult) {
                    WebSocket_Send("toggleStage");
                }
            });
        } else {
            WebSocket_Send("toggleStage");
        }
    },
};    

$(function(){

    // Reload nach Abbruch der WebSocket Verbindung    
    $("#button-reloadpage").dxButton($.extend(true, {}, metalButtonOptions, {
        disabled: false,
        icon: "fas fa-plug",
        width: "28vmin",
        height: "28vmin",
        elementAttr: {
            style: "color: var(--tm-blue)",
        },
        onClick: function(e) {
           location.reload();
         },
    }));   

});

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
            return Math.round(distance * 1000) + " m";
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

// Formatierung von Zeitangaben
    
    function formatTime(time) {
        return formatNumber(time, 0) + " sek";
    };

// Formatierung von Zahlen mit standardmäßig zwei Nachkommastellen

    function formatNumber(value, digits=2) {
        return parseFloat(value).toLocaleString('de-DE', {minimumFractionDigits: digits, maximumFractionDigits: digits})
    }

// DEBUG

    function mynotify(msg) {
        DevExpress.ui.notify(msg, "info");
    };