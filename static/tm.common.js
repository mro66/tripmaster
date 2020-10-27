var kmLeftInSector = 0;
var kmSectorPreset = 0;
var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;

$(function(){

    // Reload nach Abbruch der WebSocket Verbindung
	
		$("#button-reloadpage").dxButton({
			text: "Neu verbinden",
			type: "danger",
			visible: false,
			width: "90%",
			onClick: function(data) {
			   location.reload();
			 },
		});   
	
	// Lineare Anzeige des Etappenfortschritts
	
		var kmSectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge({
		   animation: {
				enabled: true,
				easing: "linear"
			},
			geometry: {
				orientation: "vertical"
			},
			value: 0,
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
							return Number.parseFloat(kmSectorPreset).toFixed(1) + " km &#10003;";
						} else  {
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
						size: "6vw",
						color: "gray",
					},
				},
			},
			size: {
				height: "100%",
			},
		}).dxLinearGauge("instance");
		
});

// Farbverlauf der Nebenwerte der Linearen Anzeige

	function setKmSector(fracSectorDriven) {
		var kmsectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge('instance');
		var colorConst = 153;
		var breakConst = 75;
		var redValue = colorConst;
		var greenValue = fracSectorDriven * colorConst / breakConst;
		if (fracSectorDriven > breakConst) {
			redValue = colorConst - (fracSectorDriven - breakConst) * colorConst / (100 - breakConst);
			greenValue = colorConst;
		};
		kmsectorLinearGauge.option("subvalueIndicator.color", "rgb(" + redValue + "," + greenValue + ",0)");
		kmsectorLinearGauge.option("valueIndicator.color", "rgb(" + redValue + "," + greenValue + ",0)");
		if (fracSectorDriven > 0) {
			kmsectorLinearGauge.option("subvalues", [fracSectorDriven]);
		} else {
			kmsectorLinearGauge.option("subvalues", []);
		};
		kmsectorLinearGauge.option("value", fracSectorDriven);
	};

// Formatierung von Entfernungsangaben: unter 1 km in Metern, darüber in Kilometer mit einer Nachkommastelle	
	
	function formatDistance(valDistance) {
		if (valDistance < 1) {
			return (valDistance * 1000) + " m";
		} else {
			return Number.parseFloat(valDistance).toFixed(1) + " km";
		}
	};
