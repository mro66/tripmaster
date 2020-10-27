var kmSectorToBeDriven = 0;
var kmSectorPreset = 0;

$(function(){

    // Neu laden
	var reloadPageButton = $("#button-reloadpage").dxButton({
        text: "Neu verbinden",
        type: "danger",
		visible: false,
		width: "100%",
		onClick: function(data) {
		   location.reload();
         },
    }).dxButton("instance");   
	
	$("#lineargauge-kmsector").dxLinearGauge({
       animation: {
            enabled: true,
            easing: "linear"
        },
        value: 0,
        geometry: {
            orientation: "vertical"
        },
		subvalues: [],
        subvalueIndicator: {
            type: "textCloud",
            horizontalOrientation: "right",
            offset: 23,
            text: {
                customizeText: function (e) {
					if (e.value == 100) {
						return Number.parseFloat(kmSectorPreset).toFixed(1) + " km &#10003;";
					} else  {
						if (kmSectorToBeDriven > 1) {
							return "-" + Number.parseFloat(kmSectorToBeDriven).toFixed(1) + " km";
						} else if (kmSectorToBeDriven >= 0){
							return "-" + (kmSectorToBeDriven*1000) + " m";
						} 
					}
                }
			}
        },
        scale: {
            tickInterval: 20,
			label: {
				customizeText: function (e) {
					return e.value+" %";
				}
			}
        },
		size: {
			width: 180
		},
	});
});

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
	if (fracSectorDriven > 0) {
		kmsectorLinearGauge.option("subvalues", [fracSectorDriven]);
	} else {
		kmsectorLinearGauge.option("subvalues", []);
	}
	kmsectorLinearGauge.option("value", fracSectorDriven);
};

