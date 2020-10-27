$(function(){

	// Das TabPanel im oberen Teil der ContentBox
	
		var settingsTabPanel = $("#tabPanelContainer").dxTabPanel({
			deferRendering: false,
			height: function(e) {
				return window.innerHeight;
			},
			loop: true,
			selectedIndex: 0,
			items: [{
				"title": 'Abschnitt',
				template: $("#abschnittTab"),
			}, {
				"title": 'GLP',
				template: $("#glpTab"),
			}, {
				"title": 'Setup',
				template: $("#setupTab"),
			}],
		}).dxTabPanel("instance");

	// Tab abschnittTab

		var resetSectorButton = $("#button-resetsector").dxButton({
			type: "danger",
			text: "Zähler zurücksetzen",
		    onClick: function(e) {
				sectorPresetTextBox.option("value", "-,-- km");
				// sector1000mNumberbox.reset();
				// sector100mNumberbox.reset();
				sectorReverseSwitch.option("value", false);
				mylog(audioElement.muted);
				audioElement.play();
				WebSocket_Send('resetSector');
			},
		}).dxButton("instance");   
	
		var sector1000mNumberbox = $("#numberbox-sector1000m").dxNumberBox({
			min: 0, max: 12,
			value: 0,
			format: "#0 km",
			showSpinButtons: true,
			useLargeSpinButtons: true,
			onValueChanged: function (e) {
				setSectorLength();
				if (e.value == null) {
					e.component.option("value", 0);
				}					
			},
		}).dxNumberBox("instance");
			
		var sector100mNumberbox = $("#numberbox-sector100m").dxNumberBox({
			min: -1, max: 1000,
			value: 0,
			step: 50,
			format: "#0 m",
			showSpinButtons: true,
			useLargeSpinButtons: true,
			onValueChanged: function (e) {
				setSectorLength();
				if (e.value == e.component.option("max")) {
					e.component.option("value", 0);
					sector1000mNumberbox.option("value", sector1000mNumberbox.option("value")+1);
				} else if (e.value == e.component.option("min")) {
					if (getSectorLength() > 0) {
						e.component.option("value", e.component.option("max")-e.component.option("step"));
						sector1000mNumberbox.option("value", sector1000mNumberbox.option("value")-1);
					} else {
						e.component.option("value", 0);
					}
				} else if (e.value == null) {
					e.component.option("value", 0);
				}					
			},		
		}).dxNumberBox("instance");

		var setSectorButton = $("#button-setsector").dxButton({
			type: "success",
			text: "Vorgabe einstellen",
			disabled: true,
			onClick: function(e) {
				WebSocket_Send('setSectorLength:'+getSectorLength());
				sector1000mNumberbox.reset();
				sector100mNumberbox.reset();
				sectorReverseSwitch.option("value", false);
			},
		}).dxButton("instance");   

		function getSectorLength() {
			return parseFloat(sector1000mNumberbox.option("value") + 
							  sector100mNumberbox.option("value")/1000).toFixed(2);
		};
		
		function setSectorLength() {
			var sectorLength = getSectorLength();
			if (sectorLength > 0.0) {
				setSectorButton.option("disabled", false);
				setSectorButton.option("text", "Vorgabe auf "+formatNumber(sectorLength)+" km setzen");
			} else {
				setSectorButton.option("text", "Vorgabe einstellen");
				setSectorButton.option("disabled", true);
			}
		};
		
		// Zwei Spalten Layout
		
		$(".box-twocolumn").dxBox({
			direction: "row",
			width: "100%",
			crossAlign: "start",
		});
	
		var sectorPresetTextBox = $("#textbox-sectorpreset").dxTextBox({
			readOnly: true,
			width: 110,
			value: "-,-- km",
			onValueChanged: function(e) {
				if (e.value == formatDistance(0)) {
					e.component.option("value", "-,-- km");
				}
			},
		}).dxTextBox("instance");

		var sectorTextBox = $("#textbox-sector").dxTextBox({
			readOnly: true,
			width: 110,
		}).dxTextBox("instance");

        var sectorReverseSwitch = $("#switch-sectorreverse").dxSwitch({
			onValueChanged: function(e) {
				WebSocket_Send("toggleSectorReverse");
				if (e.value === true) {
					sectorTextBox.option("elementAttr.style", "border: 1px #d9534f solid")						
				} else {
					sectorTextBox.option("elementAttr.style", "border: 1px #f4f4f4 solid")
				}
			},
			onContentReady: function(e) {
				e.component.option("value", (SECTOR_REVERSE === false));
				if (SECTOR_REVERSE === false) {
					sectorTextBox.option("elementAttr.style", "border: 1px #d9534f solid")						
				} else {
					sectorTextBox.option("elementAttr.style", "border: 1px #f4f4f4 solid")
				}
			},
        }).dxSwitch("instance");

	// Tab glpTab
	
		var glpKmSelectBox = $("#selectbox-glpkm").dxSelectBox({
			"items": [
				"1 km",
				"2 km",
				"3 km",
				"4 km",
				"5 km",
				"6 km",
				"7 km",
				"8 km",
				"9 km",
				"10 km",
				"11 km",
				"12 km",
			],
			placeholder: "Kilometer",
			onValueChanged: function(self) {
				//setSectorButton.option("disabled", false);
				//setSectorButton.option("text", "Abschnitt: "+getSectorLength()+" km");
			},
		}).dxSelectBox("instance");

		var glp100mSelectBox = $("#selectbox-glp100m").dxSelectBox({
			"items": [
				"0 m",
				"100 m",
				"200 m",
				"300 m",
				"400 m",
				"500 m",
				"600 m",
				"700 m",
				"800 m",
				"900 m",
			],
			placeholder: "Meter",
			onValueChanged: function(self) {
				//setSectorButton.option("text", "Abschnitt: "+getSectorLength()+" km");
			},
		}).dxSelectBox("instance");

	// Tab Setup

        $("#switch-pausetripmaster").dxSwitch({
            value: false,
			onValueChanged: function(e) {
				// e.event ist undefined bei programmatischem valueChange
				if(e.event !== undefined) {
					if (e.value === true) {
						WebSocket_Send('pauseMaster');
					} else {
						WebSocket_Send('startMaster');
					}
				}
			},
        });

		var tyreSizeNumberBox = $("#numberbox-tyre-size").dxNumberBox({
			min: 0, max: 200,
			value: TYRE_SIZE,
			format: "#0 cm",
			width: "70%",
			onFocusIn: function (e) {
				setTyreSizeButton.option("disabled", false);
			},
		}).dxNumberBox("instance");
		
		var setTyreSizeButton = $("#button-set-tyre-size").dxButton({
			icon: "save",
			width: "25%",
			disabled: true,
			onClick: function(e) { 
				WebSocket_Send('Radumfang:'+tyreSizeNumberBox.option("value"));
				TYRE_SIZE = tyreSizeNumberBox.option("value");
				e.component.option("disabled", true);
			},
		}).dxButton("instance");
				
		$("#button-reset-tripmaster").dxButton({
			text: "Tripmaster zurücksetzen",
			type: "danger",
			visible: true,
			elementAttr: {
				style: "margin-top: 75px",
			},
			onClick: function(e) {
				confirmDialogResetTripmaster().show().done(function (dialogResult) {
					if (dialogResult) {
						WebSocket_Send('resetTripmaster');
					}
				});
			},
		});   
	
		function confirmDialogResetTripmaster() {
			return DevExpress.ui.dialog.custom({
				title: "Tripmaster zurücksetzen",
				message: "Bist Du sicher?",
				buttons: [
					{ text: "Ja", onClick: function () { return true } },
					{ text: "Nein", onClick: function () { return false } }
				]
			});
		};

});
