// Bildschirmdimension zum Skalieren
// var windowDiagonal = Math.sqrt(Math.pow(window.innerHeight, 2) + Math.pow(window.innerWidth, 2))/1000;
var vmin = Math.sqrt(Math.pow(window.innerHeight, 2))/550;
var vmin1 = 1 / vmin;
var AVG_KMH_PRESET = 0;
var audioClick = document.createElement('audio');
audioClick.setAttribute('src', '/static/Click.ogg');

var subValueIndicator = {
    value: "gray",
    handler() {
        document.getElementById("circulargauge-speed").getElementsByClassName('dxg-subvalue-indicator')[0].style.fill = "var(--tm-" + this.value + ")";
    },
    get color() {
        return this.value;
    },
    set color(value) {
        if (value != this.value) {
            this.value = value;
            this.handler();
        };
    },
};

// Farbverlauf der Linearen Anzeige
    function setKmSector(fracSectorDriven) {
        if (fracSectorDriven <= 10) { rgbColor = "rgb(217,83,79)" } else
        if (fracSectorDriven <= 20) { rgbColor = "rgb(222,101,79)" } else
        if (fracSectorDriven <= 30) { rgbColor = "rgb(226,119,79)" } else
        if (fracSectorDriven <= 40) { rgbColor = "rgb(231,137,78)" } else
        if (fracSectorDriven <= 50) { rgbColor = "rgb(235,155,78)" } else
        if (fracSectorDriven <= 60) { rgbColor = "rgb(240,173,78)" } else
        if (fracSectorDriven <= 70) { rgbColor = "rgb(203,176,82)" } else
        if (fracSectorDriven <= 80) { rgbColor = "rgb(166,179,85)" } else
        if (fracSectorDriven <= 90) { rgbColor = "rgb(129,181,89)" } else
        if (fracSectorDriven <= 100) { rgbColor = "rgb(92,184,92)" }
        document.getElementById("lineargauge-kmsector").getElementsByClassName('dxg-subvalue-indicator')[1].style.fill = rgbColor;
        document.getElementById("lineargauge-kmsector").getElementsByClassName('dxg-main-bar')[0].style.fill = rgbColor;
    };


$(function(){

    // Multiview
    $("#multiview-dashboard").dxMultiView({
        height: "100%",
        selectedIndex: 1,
        loop: false,
        animationEnabled: true,
        deferRendering: false,
        items: [{
            template: $("#mv-clock"),
        }, {
            template: $("#mv-sector"),
        }, {
            template: $("#mv-regtest"),
        }],
    });
    
    // Box
    $(".dashboard-box").dxBox({
        width: "100%",
        height: "100%",
    });

// Multiview Uhr

    $("#circulargauge-cputemp").dxCircularGauge({
        // "containerBackgroundColor": "black",
        geometry: {
            endAngle: 225,
            startAngle: 315
        },
        rangeContainer: {
            backgroundColor: "var(--tm-digit)",
            offset: 8,
            orientation: "outside",
            width: 8,
            ranges: [
               {
                color: "var(--tm-red)",
                startValue: 80,
                endValue: 70
               },
               {
                color: "var(--tm-yellow)",
                startValue: 70,
                endValue: 60
               },
               {
                color: "var(--tm-green)",
                startValue: 60,
                endValue: 40
               },
            ],
           },
        scale: {
            endValue: 40,
            startValue: 80,
            label: {
                font: {
                    family: "Tripmaster Font",
                    color: "var(--tm-digit)",
                    size: 25*vmin, // 30,
                },
                indentFromTick: -20,
            },
            orientation: "inside",
            tickInterval: 10,
            tick: {
                color: "var(--tm-digit)",
                length: 16*vmin, // 16,
                width: 4
                },
        },
        title: {
            text: "Temp",
            verticalAlignment: "bottom",
            font: {
                family: "Tripmaster Font",
                color: "var(--tm-digit)",
                size: 25*vmin, // 30,
            },
        },
        valueIndicator: {
            color: "var(--tm-digit)",
            indentFromCenter: 120*vmin1, // 120,
            spindleGapSize: 0,
            spindleSize: 0,
            offset: 0,
            type: "triangleNeedle",
            width: 10*vmin, // 10,
        },
    });

// Multiview Tacho

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
                color: "var(--tm-gray)",
                length: 22*vmin,
                width: 5*vmin,
            },
            tickInterval: 10,
            minorTick: {
                color: "Ivory",
                visible: true,
                length: 15*vmin,
                width: 2*vmin,
            },
            minorTickInterval: 2,
            orientation: "inside",
            label: {
                font: {
                    color: "var(--tm-gray)", 
                    size: 42*vmin, 
                    family: "Tripmaster Font" 
                },
                indentFromTick: -30*vmin,
           }
        },
        rangeContainer: {
            backgroundColor: "black",
            offset: 15*vmin,
            width: 15*vmin,
        },
        value: 0,
        valueIndicator: {
            type: "twoColorNeedle",
            color: "black",
            secondFraction: 0.5,
            secondColor: "var(--tm-gray)",
            offset: 0,
            width: 7*vmin,
            indentFromCenter: 25*vmin,
            spindleGapSize: 20*vmin,
            spindleSize: 50*vmin,
        },
        subvalues: [0],
        subvalueIndicator: {
            type: "triangleMarker",
            offset: -5*vmin,
            length: 20*vmin,
            width: 20*vmin,
            
        },
        redrawOnResize: true,
        onInitialized: function(e) {
            e.element.click(function() {
                if (stageStarted.status) {
                    audioClick.play().catch(function(error) { });
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
            size: 15*vmin,
        },
        subvalues: [],
        subvalueIndicator: {
            type: "textCloud",
            horizontalOrientation: "right",
            offset: 35*vmin,
            arrowLength: 15*vmin,
            text: {
                font: {
                    family: "Tripmaster Font", 
                    size: "6vmin",
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
        rangeContainer: {
            horizontalOrientation: "center",
            width: {
                start: 10*vmin,
                end: 10*vmin,
            },
            offset: -5*vmin,
        },
        scale: {
            tick: {
                width: 5*vmin,
                color: "var(--tm-red)",
                length: 15*vmin,
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
    // Start/Stop Etappe
    $("#button-togglestage").dxButton($.extend(true, {}, metalButtonOptions, toggleStageButtonOptions, {
    })); 

    $("#button-1").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

    $("#button-2").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

    $("#button-3").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

    $("#button-4").dxButton($.extend(true, {}, metalButtonOptions, {
    })); 

// Multiview GLP

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
                length: 6*vmin,
                width: 3*vmin
            },
            minorTickInterval: 10,
            minorTick: {
                length: 6*vmin,
                width: 3*vmin,
                visible: true
            },
            label: {
                visible: true,
                indentFromTick: -120*vmin,
                useRangeColors: true,
                font: {
                    size: "8vmin",
                    family: "Tripmaster Font",
                    weight: "lighter"
                },
                customizeText: function(arg) {
                    return formatSpeed(0);
                }
            }
        },
        rangeContainer: {
            width: 10*vmin,
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
            offset: 60*vmin,
            size: 10*vmin,
            text: {
                indent: 15*vmin,
                font: {
                    color: "var(--tm-blue)",
                    size: "5.3vmin",
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
            offset: 60*vmin,
            baseValue: 0,
            color: "var(--tm-blue)",
            width: 13*vmin,
            indentFromCenter: 150*vmin,
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
    var odoKmStage = document.getElementById("odometer-kmstage");
    var odoKmSector = document.getElementById("odometer-kmsector");
    var statusGPS = document.getElementById("status-gps");
    var statusTyre = document.getElementById("status-tyre");
    
    //top ...
    // kmstage
    odoKmStage.style.top = y - spindleSize - parseFloat(odoKmStage.clientHeight) + "px";
    // kmsector
    odoKmSector.style.top = y + spindleSize + "px";
    // gps
    statusGPS.style.top = y - statusGPS.clientHeight / 2 + "px";
    // tyre
    statusTyre.style.top = y - statusTyre.clientHeight / 2 + "px";
    // ... und left
    // kmstage
    odoKmStage.style.left = x - odoKmStage.clientWidth / 2 + "px";
    odoKmStage.style.visibility = "visible";
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

