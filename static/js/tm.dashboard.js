// Bildschirmdiagonale zum Skalieren
var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;
var AVG_KMH_PRESET = 0;

$(function(){

	// Multiview

    $("#multiview-dashboard").dxMultiView({
        height: "100%",
        selectedIndex: 0,
        loop: false,
        animationEnabled: true,
		deferRendering: false,
		items: [{
			template: $("#mv-sector"),
		}, {
			template: $("#mv-regtest"),
		}],
        onSelectionChanged: function(e) {
			if (e.component.option("selectedIndex")==1) {
                // document.getElementById("lineargauge-kmsector").style.display = "block";
                // document.getElementById("status-information").style.display = "block";
				// $("#lineargauge-kmsector").appendTo("#right-regtest");
			} else {
				// $("#lineargauge-kmsector").appendTo("#right-sector");
                // document.getElementById("lineargauge-kmsector").style.display = "none";
			}
        }
    });
    
	// Box mit zwei Spalten
		
	$(".twocolumn-box").dxBox({
		direction: "row",
		width: "100%",
		height: "100%",
	});

   $("#circulargauge-speed").dxCircularGauge({
        containerBackgroundColor: "Ivory",
		animation: {
            enabled: true,
            easing: "linear"
        },
		scale: {
            startValue: 0, 
            endValue: 150,
            tick: {
                color: "gray",
                length: 20 * windowDiagonal,
                width: 5 * windowDiagonal,
            },
            tickInterval: 10,
            minorTick: {
                color: "Ivory",
                visible: true,
                length: 15 * windowDiagonal,
				width: 2 * windowDiagonal,
            },
            minorTickInterval: 2,
            orientation: "inside",
            label: {
        		font: {color: "gray", size: "4.5vw", family: "Tripmaster Font" },
                indentFromTick: -25 * windowDiagonal,
           }
        },
        rangeContainer: {
            backgroundColor: "black",
            offset: 15 * windowDiagonal,
            width: 15 * windowDiagonal,
        },
        value: 0,
        valueIndicator: {
            type: "twoColorNeedle",
            color: "black",
            secondFraction: 0.5,
            secondColor: "gray",
            offset: 0,
            width: 7 * windowDiagonal,
            indentFromCenter: 25 * windowDiagonal,
            spindleGapSize: 20 * windowDiagonal,
            spindleSize: 50 * windowDiagonal,
        },
        subvalues: [0],
        subvalueIndicator: {
			type: "triangleMarker",
            offset: -5 * windowDiagonal,
			length: 20 * windowDiagonal,
			width: 20 * windowDiagonal,
        },
		redrawOnResize: true,
    });

 
	$("#lineargauge-kmsector").dxLinearGauge($.extend(true, {}, linearGaugeOptions, {
		elementAttr: {
            // style: "display: block",
		},
		size: {
			height: window.innerHeight,
            width: function(e) { return e.element.width(); },
		},
		rangeContainer: {
			width: 5 * windowDiagonal,
		},
		scale: {
			label: {
				font: {
					size: "3vw",
					family: "Tripmaster Font", 
				}
			}
		},
		subvalueIndicator: {
			text: {
				font: {
					size: "3vw",
					family: "Tripmaster Font", 
				}
			},
			arrowLength: 15 * windowDiagonal,
			offset: 25 * windowDiagonal,
		},
		valueIndicator: {
			size: 10 * windowDiagonal,
		},
	}));
		
	// Gemeinsame Optionen der Statusbuttons
	var buttonOptions = {
		elementAttr: {
			class: "statusbutton",
			style: "color: lightgray",
		},
		focusStateEnabled: false,
		hoverStateEnabled: false,
	};
	
	$("#button-togglerecording").dxButton($.extend(true, {}, buttonOptions, {
		icon: "fas fa-circle",
		elementAttr: {
			style: "color: var(--tm-red);",
            class: "statusbutton small",
		},
		onClick: function(e) {
			WebSocket_Send('toggleRecording');
		},
	})); 

	var roundaboutButton = $("#button-roundabout").dxButton($.extend(true, {}, buttonOptions, {
		icon: "fas fa-sync",
		elementAttr: {
			style: "color: var(--tm-blue)",
		},
		onClick: function(e) {
			mynotify("Kreisverkehr Button gedrückt");
		},
	})).dxButton("instance"); 

	var roundaboutButton = $("#button-townsign").dxButton($.extend(true, {}, buttonOptions, {
		icon: "fas fa-sign",
		elementAttr: {
			style: "color: var(--tm-yellow)",
		},
		onClick: function(e) {
			mynotify("Ortseingangs Button gedrückt");
		},
	})).dxButton("instance"); 

	var checkpointButton = $("#button-checkpoint").dxButton($.extend(true, {}, buttonOptions, {
		icon: "fas fa-map-marker-alt",
		elementAttr: {
			style: "color: var(--tm-green)",
		},
		onClick: function(e) {
			mynotify("OK Button gedrückt");
		},
	})).dxButton("instance"); 


	$("#circulargauge-devavgspeed").dxCircularGauge({
		animation: {
			enabled: true,
			easing: "linear"
		},
		geometry: {
			startAngle: 150,
			endAngle: 30
		},
		size: {
			height: window.innerHeight * 0.7,
		},
		scale: {
			startValue: -25,
			endValue: 25,
			tickInterval: 30,
			tick: {
				length: 6 * windowDiagonal,
				width: 3 * windowDiagonal
			},
			minorTickInterval: 10,
			minorTick: {
				length: 6 * windowDiagonal,
				width: 3 * windowDiagonal,
				visible: true
			},
			label: {
				visible: true,
				indentFromTick: -120 * windowDiagonal,
				useRangeColors: true,
				font: {
					size: "4.5vw",
					family: "Tripmaster Font",
					weight: "lighter"
				},
				customizeText: function(arg) {
					return formatSpeed(0);
				}
			}
		},
		rangeContainer: {
			width: 7 * windowDiagonal,
			palette: [
				"var(--tm-red)",
				"var(--tm-yellow)",
				"var(--tm-green)",
				"var(--tm-yellow)",
				"var(--tm-red)"
			],
			ranges: [
				{ startValue: -25, endValue: -15 },
				{ startValue: -15, endValue: -5 },
				{ startValue: -5, endValue: 5 },
				{ startValue: 5, endValue: 15 },
				{ startValue: 15, endValue: 25 }
			]
		},
		value: 0,
		valueIndicator: {
			type: "rangeBar",
			color: "var(--tm-blue)",
			baseValue: 0,
			offset: 60 * windowDiagonal,
			size: 10 * windowDiagonal,
			text: {
				indent: 15 * windowDiagonal,
				font: {
					color: "var(--tm-blue)",
					size: "3vw",
					family: "Tripmaster Font"
				},
				customizeText: function(arg) {
					prefix = "";
					if((arg.value == 25.0) || (arg.value == -25.0)) {
						return "";
					} else {
						return prefix + formatSpeed(arg.value + AVG_KMH_PRESET);
					};
				}
			}
		},
		subvalues: [0],
		subvalueIndicator: {
			type: "TriangleNeedle",
			offset: 60 * windowDiagonal,
			baseValue: 0,
			color: "var(--tm-blue)",
			width: 13 * windowDiagonal,
			indentFromCenter: 150 * windowDiagonal,
			spindleSize: 0
		},
		// redrawOnResize: true,
		onOptionChanged: function(e) {
			var subValueIndicator = document.querySelectorAll('#circulargauge-devavgspeed .dxg-subvalue-indicator')[0];
			var valueIndicator = document.querySelectorAll('#circulargauge-devavgspeed .dxg-value-indicator')[0];
			var valueIndicatorText = document.querySelectorAll('#circulargauge-devavgspeed .dxg-text')[0];
			if(Math.abs(e.value) > 15) {
				subValueIndicator.setAttribute('fill', "var(--tm-red)");
				valueIndicator.setAttribute('fill', "var(--tm-red)");
				valueIndicatorText.setAttribute('fill', "var(--tm-red)");
			} else if(Math.abs(e.value) > 5) {
				subValueIndicator.setAttribute('fill', "var(--tm-yellow)");
				valueIndicator.setAttribute('fill', "var(--tm-yellow)");
				valueIndicatorText.setAttribute('fill', "var(--tm-yellow)");
			} else {
				subValueIndicator.setAttribute('fill', "var(--tm-green)");
				valueIndicator.setAttribute('fill', "var(--tm-green)");
				valueIndicatorText.setAttribute('fill', "var(--tm-green)");
			}			
		},
	});

	$("#textbox-regtestseconds").dxTextBox($.extend(true, {}, textBoxOptions,{
		value: "0 sek",
	}));
		
});

function resizeAndPosition() {

	// Anzeigen neu zeichnen
	var speedCircularGauge = $("#circulargauge-speed").dxCircularGauge('instance')
	speedCircularGauge.render();
	// var kmSectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge('instance');
	// kmSectorLinearGauge.option("size.height", window.innerHeight);
	// kmSectorLinearGauge.render();
	
	var x = parseFloat(document.getElementsByClassName("dxg-spindle-hole")[0].getAttribute('cx'));
	var y = parseFloat(document.getElementsByClassName("dxg-spindle-hole")[0].getAttribute('cy'));
	var spindleSize = parseFloat(speedCircularGauge.option("valueIndicator.spindleSize"));
    
	// Elemente an der Mitte des Tachos ausrichten
	var odoKmTotal = document.getElementById("odometer-kmtotal");
	var odoKmSector = document.getElementById("odometer-kmsector");
	var statusGPS = document.getElementById("status-gps");
	var statusTyre = document.getElementById("status-tyre");
	
	//top ...
	// kmtotal
	odoKmTotal.style.top = y - spindleSize - parseFloat(odoKmTotal.clientHeight) + "px";
	// kmsector
	odoKmSector.style.top = y + spindleSize + "px";
    // gps
    statusGPS.style.top = y - statusGPS.clientHeight / 2 + "px";
    // tyre
    statusTyre.style.top = y - statusTyre.clientHeight / 2 + "px";
	// ... und left
	// kmtotal
	odoKmTotal.style.left = x - odoKmTotal.clientWidth / 2 + "px";
	odoKmTotal.style.visibility = "visible";
	// kmsector
	odoKmSector.style.left = x - odoKmSector.clientWidth / 2 + "px";
	odoKmSector.style.visibility = "visible";
    // gps
    statusGPS.style.left = x - statusGPS.clientWidth / 2 - spindleSize * 2 + "px";
    statusGPS.style.visibility = "visible";
    // tyre
    statusTyre.style.left = x - statusTyre.clientWidth / 2 + spindleSize * 2 + "px";
	statusTyre.style.visibility = "visible";
    
    // document.getElementById("lineargauge-kmsector").style.display = "none";
    // document.getElementById("status-information").style.display = "";
    
    
};