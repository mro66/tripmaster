var kmLeftInSector = 0;
var kmSectorPreset = 0;
var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;

// Gemeinsame Optionen ...

// ...der linearen Anzeige des Etappenfortschritts
var linearGaugeOptions = {
   animation: {
		enabled: true,
		easing: "linear"
	},
	geometry: {
		orientation: "vertical"
	},
	size: {
		height: "100%",
		width: "100%",
	},
	subvalues: [],
	subvalueIndicator: {
		type: "textCloud",
		horizontalOrientation: "right",
		offset: 23,
		arrowLength: 5,
		text: {
			font: {
				size: "5vw",
				color: "Ivory",
			},
			customizeText: function (e) {
				if (e.value == 100) {
					return formatNumber(kmSectorPreset) + " km &#10003;";
				} else {
					return "-" + formatDistance(kmLeftInSector);
				}
			}
		}
	},
	scale: {
		tickInterval: 20,
		label: {
			customizeText: function (e) {
				return e.value+" %";
			},
			font: {
				size: "5vw",
				color: "gray",
			},
		},
	},
	redrawOnResize: true,
};

// ... der Anzeigetextboxen
var textBoxOptions = {
	readOnly: true,
	focusStateEnabled: false,
	hoverStateEnabled: false,	
};

$(function(){

    // Reload nach Abbruch der WebSocket Verbindung
	
		$("#button-reloadpage").dxButton({
			text: "Neu verbinden",
			type: "danger",
			visible: false,
			width: "90%",
			onClick: function(e) {
			   location.reload();
			 },
		});   
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