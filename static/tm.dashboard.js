$(function(){

    var speedCircularGauge = $("#circulargauge-speed").dxCircularGauge({
        animation: {
            enabled: true,
            easing: "linear"
        },
		elementAttr: {
			style: "float: left"
		},
		scale: {
            startValue: 0, 
            endValue: 150,
            tick: {
                color: "gray",
                length: 15,
                width: 4
            },
            tickInterval: 10,
            minorTick: {
                color: "white",
                length: 10,
                visible: true
            },
            minorTickInterval: 2,
            orientation: "inside",
            label: {
                indentFromTick: -20,
        		font: {color: "gray", size: 20, family: "Alternate Gothic" },
            }
        },
        rangeContainer: {
            offset: 10,
            backgroundColor: "black",
            width: 9
        },
        value: 75,
        valueIndicator: {
            type: "twoColorNeedle",
            color: "black",
            secondFraction: 0.5,
            secondColor: "gray",
            width: 3,
            offset: 0,
            indentFromCenter: 25,
            spindleGapSize: 20,
            spindleSize: 50
        },
        subvalues: [0],
        subvalueIndicator: {
            offset: -5
        }
    }).dxCircularGauge("instance");
		
});
