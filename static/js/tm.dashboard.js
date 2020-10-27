// Bildschirmdimension zum Skalieren
// var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;
var vh = Math.sqrt(Math.pow(window.innerHeight, 2))/550;
var AVG_KMH_PRESET = 0;

var subValueIndicator = {
    value: "red",
    listener() {
        speedGauge.option("subvalueIndicator", {"color": "var(--tm-" + this.value + ")"});
    },
    get color() {
        return this.value;
    },
    set color(value) {
        if (value != this.value) {
            this.value = value;
            this.listener();
        };
    },
};



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
            easing: "linear",
        },
        scale: {
            startValue: 0, 
            endValue: 150,
            tick: {
                color: "gray",
                length: 22*vh,
                width: 5*vh,
            },
            tickInterval: 10,
            minorTick: {
                color: "Ivory",
                visible: true,
                length: 15*vh,
                width: 2*vh,
            },
            minorTickInterval: 2,
            orientation: "inside",
            label: {
                font: {
                    color: "gray", 
                    size: 42*vh, 
                    family: "Tripmaster Font" 
                },
                indentFromTick: -30*vh,
           }
        },
        rangeContainer: {
            backgroundColor: "black",
            offset: 15*vh,
            width: 15*vh,
        },
        value: 0,
        valueIndicator: {
            type: "twoColorNeedle",
            color: "black",
            secondFraction: 0.5,
            secondColor: "gray",
            offset: 0,
            width: 7*vh,
            indentFromCenter: 25*vh,
            spindleGapSize: 20*vh,
            spindleSize: 50*vh,
        },
        subvalues: [0],
        subvalueIndicator: {
            type: "triangleMarker",
            offset: -5*vh,
            length: 20*vh,
            width: 20*vh,
            
        },
        redrawOnResize: true,
        onInitialized: function(e) {
            e.element.click(function() {
                if (stageStart.status) {
                    window.navigator.vibrate(200);
                    WebSocket_Send('resetSector');
                } else {
                    DevExpress.ui.notify("Etappe noch nicht gestartet", "warning")
                };
            });
        },
    });
 
    $("#lineargauge-kmsector").dxLinearGauge({
        elementAttr: {
            style: "display: flex; justify-content: center;",
        },
        size: {
            height: window.innerHeight,
            width: function(e) { return e.element.width(); },
        },
       animation: {
            enabled: true,
            easing: "linear"
        },
        geometry: {
            orientation: "vertical"
        },
        valueIndicator: {
            size: 15*vh,
        },
        subvalues: [],
        subvalueIndicator: {
            type: "textCloud",
            horizontalOrientation: "right",
            offset: 35*vh,
            arrowLength: 15*vh,
            text: {
                font: {
                    family: "Tripmaster Font", 
                    size: "3.5vmax",
                    color: "Ivory",
                },
                customizeText: function (e) {
                    if (e.value == 100) {
                        // $("#lineargauge-kmsector").dxLinearGauge('instance').option("subvalueIndicator.color", "var(--tm-green)");
                        return formatNumber(kmSectorPreset) + " km &#10003;";
                    } else {
                        return "-" + formatDistance(kmLeftInSector);
                    }
                }
            }
        },
        rangeContainer: {
            horizontalOrientation: "center",
            width: {
                start: 10*vh,
                end: 10*vh,
            },
            offset: -5*vh,
        },
        scale: {
            tick: {
                width: 5*vh,
                color: "var(--tm-red)",
                length: 15*vh,
            },
            tickInterval: 25,
            horizontalOrientation: "left",
            label: {
                visible: false,
            },
        },
        redrawOnResize: true,
        onInitialized: function(e) {
            e.element.click(function() {
                if (e.element.parent().get(0).id == "right-sector") {
                    buttonsToFront();
                    setTimeout(function() {
                        linearGaugeToFront();
                    }, 5000);
                }
            });
        },
    });
    
    // Buttons
    $("#button-1").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

    $("#button-2").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

    $("#button-3").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

    $("#button-4").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

// GLP
    // Abweichung von der Durchschnittsgeschwindigkeit
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
                length: 6*vh,
                width: 3*vh
            },
            minorTickInterval: 10,
            minorTick: {
                length: 6*vh,
                width: 3*vh,
                visible: true
            },
            label: {
                visible: true,
                indentFromTick: -120*vh,
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
            width: 7*vh,
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
            offset: 60*vh,
            size: 10*vh,
            text: {
                indent: 15*vh,
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
            offset: 60*vh,
            baseValue: 0,
            color: "var(--tm-blue)",
            width: 13*vh,
            indentFromCenter: 150*vh,
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

    // Restfahrzeit
    $("#textbox-regtesttime").dxTextBox($.extend(true, {}, textBoxOptions,{
        value: "0 sek",
    }));
        
});

function resizeAndPosition() {
    // Anzeigen neu zeichnen
    var speedCircularGauge = $("#circulargauge-speed").dxCircularGauge('instance')
    speedCircularGauge.render();
    
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
   
};

function buttonsToFront() {
    $("#lineargauge-kmsector").fadeOut("slow", function(){
        $("#button-group").fadeIn("slow");
        $("#lineargauge-kmsector").appendTo("#right-regtest");
        $("#lineargauge-kmsector").fadeIn("slow");
    });
};

function linearGaugeToFront() {
    $("#lineargauge-kmsector").fadeOut("slow");
    $("#button-group").fadeOut("slow", function(){
        $("#lineargauge-kmsector").appendTo("#right-sector");
        $("#lineargauge-kmsector").fadeIn("slow");
    });
};

