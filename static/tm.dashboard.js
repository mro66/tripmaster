$(function(){


	// Zwei Spalten Layout
		
	var twoColumnBox = $("#box-twocolumn").dxBox({
		direction: "row",
		width: "100%",
		height: "100%",
	}).dxBox("instance");

    var speedCircularGauge = $("#circulargauge-speed").dxCircularGauge({
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
            },
            tickInterval: 10,
            minorTick: {
                color: "Ivory",
                visible: true,
            },
            minorTickInterval: 2,
            orientation: "inside",
            label: {
        		font: {color: "gray", size: "4vw", family: "Alternate Gothic" },
            }
        },
        rangeContainer: {
            backgroundColor: "black",
        },
        value: 0,
        valueIndicator: {
            type: "twoColorNeedle",
            color: "black",
            secondFraction: 0.5,
            secondColor: "gray",
            offset: 0,
        },
        subvalues: [0],
        subvalueIndicator: {
			type: "triangleMarker",
        },
		redrawOnResize: true,
    }).dxCircularGauge("instance");
		
});

function resizeAndPosition() {
	// Bildschirmdiagonale zum Skalieren
	var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;

	// Auf Dashboard skalieren
	// Lineare Anzeige
	kmSectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge('instance');
	kmSectorLinearGauge.option({
		size: {
			height: window.innerHeight,
		},
		rangeContainer: {
			width: 5 * windowDiagonal,
		},
		scale: {
			label: {
				font: {
					size: "3vw",
				}
			}
		},
		subvalueIndicator: {
			text: {
				font: {
					size: "3vw",
				}
			},
			arrowLength: 15 * windowDiagonal,
			offset: 25 * windowDiagonal,
		},
		valueIndicator: {
			size: 10 * windowDiagonal,
		},
	});
	
	// Tacho
	speedCircularGauge = $('#circulargauge-speed').dxCircularGauge('instance');
	speedCircularGauge.option({
		scale: {
            tick: {
                length: 15 * windowDiagonal,
                width: 4 * windowDiagonal,
            },
            minorTick: {
                length: 10 * windowDiagonal,
				width: 1 * windowDiagonal,
            },
            label: {
                indentFromTick: -20 * windowDiagonal,
            }
        },
        rangeContainer: {
            offset: 10 * windowDiagonal,
            width: 10 * windowDiagonal,
        },
        valueIndicator: {
            width: 5 * windowDiagonal,
            indentFromCenter: 25 * windowDiagonal,
            spindleGapSize: 20 * windowDiagonal,
            spindleSize: 50 * windowDiagonal,
        },
        subvalueIndicator: {
            offset: -5 * windowDiagonal,
			length: 14 * windowDiagonal,
			width: 13 * windowDiagonal,
        },
	});
	
	// Odometer
	//top ...
	// kmsector
	var halfOdoHeight = odoKmSector.clientHeight / 2;
	odoKmSector.style.top = window.innerHeight / 2.55 - halfOdoHeight + "px";
	// kmtotal
	halfOdoHeight = odoKmTotal.clientHeight / 2;
	odoKmTotal.style.top = window.innerHeight / 1.55 + halfOdoHeight + "px";
	// ... und left
	// kmsector
	var halfOdoWidth = odoKmSector.clientWidth / 2;
	odoKmSector.style.left = (window.innerWidth /3 ) - halfOdoWidth + "px";
	odoKmSector.style.visibility = "visible";
	// kmtotal
	halfOdoWidth = odoKmTotal.clientWidth / 2;
	odoKmTotal.style.left = (window.innerWidth /3 ) - halfOdoWidth + "px";
	odoKmTotal.style.visibility = "visible";
};

function fullScreen() {
	if (screenfull.enabled) {
		screenfull.toggle();
		// screen.orientation.lock("landscape-secondary");
	} 
};
function showScreensize() {
	DevExpress.ui.notify("Breite: "+window.innerWidth+", Höhe: "+window.innerHeight, "info");
};
