// Bildschirmdiagonale zum Skalieren
var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;

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
				$("#lineargauge-kmsector").appendTo("#right-regtest");
			} else {
				$("#lineargauge-kmsector").appendTo("#right-sector");
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
                length: 15 * windowDiagonal,
                width: 4 * windowDiagonal,
            },
            tickInterval: 10,
            minorTick: {
                color: "Ivory",
                visible: true,
                length: 10 * windowDiagonal,
				width: 1 * windowDiagonal,
            },
            minorTickInterval: 2,
            orientation: "inside",
            label: {
        		font: {color: "gray", size: "4vw", family: "Tripmaster Font" },
                 indentFromTick: -20 * windowDiagonal,
           }
        },
        rangeContainer: {
            backgroundColor: "black",
            offset: 10 * windowDiagonal,
            width: 10 * windowDiagonal,
        },
        value: 0,
        valueIndicator: {
            type: "twoColorNeedle",
            color: "black",
            secondFraction: 0.5,
            secondColor: "gray",
            offset: 0,
            width: 5 * windowDiagonal,
            indentFromCenter: 25 * windowDiagonal,
            spindleGapSize: 20 * windowDiagonal,
            spindleSize: 50 * windowDiagonal,
        },
        subvalues: [0],
        subvalueIndicator: {
			type: "triangleMarker",
            offset: -5 * windowDiagonal,
			length: 14 * windowDiagonal,
			width: 13 * windowDiagonal,
        },
		redrawOnResize: true,
    });

	$("#lineargauge-kmsector").dxLinearGauge($.extend(true, {}, linearGaugeOptions, {
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
		
    $("#circulargauge-devavgspeed").dxCircularGauge({
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
            tickInterval: 10,
            tick: {
                length: 6 * windowDiagonal,
                width: 3 * windowDiagonal,
            },
            label: {
                indentFromTick: 10 * windowDiagonal,
                font: { 
					color: "gray", 
					size: "2.5vw", 
					family: "Tripmaster Font", 
					weight: "lighter"
				},
                customizeText: function(arg) {
                    return arg.valueText + " km/h";
                }
            }
        },
        rangeContainer: {
            width: 7 * windowDiagonal,
        },
        valueIndicator: {
            type: "TriangleNeedle",
            offset: 0,
            color: "var(--tm-red)",
            baseValue: 0,
            width: 13 * windowDiagonal,
			indentFromCenter: 150 * windowDiagonal,
			spindleSize: 0,
        },
        value: 0,
		redrawOnResize: true,
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
	
	// Odometer an der Mitte des Tachos ausrichten
	var odoKmTotal = document.getElementById("odometer-kmtotal");
	var odoKmSector = document.getElementById("odometer-kmsector");
	
	//top ...
	// kmsector
	var x = document.getElementsByClassName("dxg-spindle-hole")[0].getAttribute('cx');
	var y = document.getElementsByClassName("dxg-spindle-hole")[0].getAttribute('cy');
	var spindleSize = speedCircularGauge.option("valueIndicator.spindleSize");
	odoKmSector.style.top = parseFloat(y) - parseFloat(spindleSize) - parseFloat(odoKmSector.clientHeight) + "px";
	// kmtotal
	odoKmTotal.style.top = parseFloat(y) + parseFloat(spindleSize) + "px";
	// ... und left
	// kmsector
	var halfOdoWidth = odoKmSector.clientWidth / 2;
	odoKmSector.style.left = parseFloat(x) - parseFloat(halfOdoWidth) + "px";
	odoKmSector.style.visibility = "visible";
	// kmtotal
	halfOdoWidth = odoKmTotal.clientWidth / 2;
	odoKmTotal.style.left = parseFloat(x) - parseFloat(halfOdoWidth) + "px";
	odoKmTotal.style.visibility = "visible";
	
};

function resetSector() {
	document.getElementById("odometer-kmsector").innerHTML = 0;
	var kmSectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge('instance');
	kmSectorLinearGauge.option("value", 0);
	kmSectorLinearGauge.option("subvalues", []);
	WebSocket_Send('resetSector');
};
