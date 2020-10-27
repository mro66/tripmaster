$(function(){

	// Das TabPanel im oberen Teil der ContentBox
	
		var settingsTabPanel = $("#tabPanelContainer").dxTabPanel({
			deferRendering: false,
			height: function() {
				return window.innerHeight;
			},
			loop: true,
			items: [{
				"title": 'Etappe',
				template: $("#etappeTab"),
			}, {
				"title": 'GLP',
				template: $("#glpTab"),
			}, {
				"title": 'Setup',
				template: $("#setupTab"),
			}],
			selectedIndex: 2,
		}).dxTabPanel("instance");

	// Tab etappeTab

		var resetSectorButton = $("#button-resetsector").dxButton({
			type: "danger",
			text: "RESET",
		    onClick: function(self) {
				WebSocket_Send('resetSector');
				sectorPresetTextBox.reset();
				sectorKmSelectBox.reset();
				sector100mSelectBox.reset();
				sectorReverseRadioGroup.option("value", yesno[1]);
			},
		}).dxButton("instance");   
	
		var sectorKmSelectBox = $("#selectbox-sectorkm").dxSelectBox({
			"items": [
				"0 km",
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
				var sectorLength = getSectorLength();
				if (sectorLength > 0.0) {
					setSectorButton.option("disabled", false);
					setSectorButton.option("text", "Etappe: "+formatNumber(sectorLength)+" km");
				} else {
					setSectorButton.option("text", "Etappe einstellen");
					setSectorButton.option("disabled", true);
				}
			},
		}).dxSelectBox("instance");

		var sector100mSelectBox = $("#selectbox-sector100m").dxSelectBox({
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
				var sectorLength = getSectorLength();
				if (sectorLength > 0.0) {
					setSectorButton.option("disabled", false);
					setSectorButton.option("text", "Etappe: "+formatNumber(sectorLength)+" km");
				} else {
					setSectorButton.option("text", "Etappe einstellen");
					setSectorButton.option("disabled", true);
				}
			},
		}).dxSelectBox("instance");

		var setSectorButton = $("#button-setsector").dxButton({
			type: "success",
			text: "Etappe einstellen",
			disabled: true,
			onClick: function(self) {
				WebSocket_Send('setSectorLength:'+getSectorLength());
				sectorKmSelectBox.reset();
				sector100mSelectBox.reset();
				sectorReverseRadioGroup.option("value", yesno[1]);
			},
		}).dxButton("instance");   

		function getSectorLength() {
			var km_int = (sectorKmSelectBox.option("value") == null) ? 0 : parseInt(sectorKmSelectBox.option("value"));
			var km_frac = (sector100mSelectBox.option("value") == null) ? 0 : parseInt(sector100mSelectBox.option("value"));
			return km_int + km_frac/1000;
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
		}).dxTextBox("instance");

		var sectorTextBox = $("#textbox-sector").dxTextBox({
			readOnly: true,
			width: 110,
		}).dxTextBox("instance");

		var sectorReverseRadioGroup = $("#radio-group-sectorreverse").dxRadioGroup({
			items: yesno,
			value: yesno[1],
			layout: "horizontal",
			onValueChanged: function(self) {
				WebSocket_Send("toggleSectorReverse");
				if (self.value == yesno[0]) {
					sectorTextBox.option("elementAttr.style", "border: 1px #d9534f solid")						
				} else {
					sectorTextBox.option("elementAttr.style", "border: 1px #f4f4f4 solid")
				}
			},
			onContentReady: function(self) {
				self.component.option("value", yesno[SECTOR_REVERSE]);
				if (SECTOR_REVERSE == 0) {
					sectorTextBox.option("elementAttr.style", "border: 1px #d9534f solid")						
				} else {
					sectorTextBox.option("elementAttr.style", "border: 1px #f4f4f4 solid")
				}
			},
		}).dxRadioGroup("instance");

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
				//setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
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
				//setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
			},
		}).dxSelectBox("instance");

	// Tab Setup

		$("#radio-group-pausetripmaster").dxRadioGroup({
			items: yesno,
			value: yesno[1],
			layout: "horizontal",
			onValueChanged: function(self) {
				// self.event ist undefined bei programmatischem valueChange
				if(self.event !== undefined) {
					if (self.value === yesno[0]) {
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
				confirmDialog().show().done(function (dialogResult) {
					if (dialogResult) {
						WebSocket_Send('Radumfang:'+tyreSizeNumberBox.option("value"));
						TYRE_SIZE = tyreSizeNumberBox.option("value");
					} else {
						tyreSizeNumberBox.option("value", TYRE_SIZE);
					}
					e.component.option("disabled", true);
				});
			}
		}).dxButton("instance");
				
		$("#button-reset-tripmaster").dxButton({
			text: "Tripmaster zurücksetzen",
			type: "danger",
			visible: true,
			elementAttr: {
				style: "margin-top: 75px",
			},
			onClick: function(self) {
			   //location.reload();
			 },
		});   
	
		function confirmDialog() {
			return DevExpress.ui.dialog.custom({
				title: "Aktion bestätigen",
				message: "Bist Du sicher?",
				buttons: [
					{ text: "Ja", onClick: function () { return true } },
					{ text: "Nein", onClick: function () { return false } }
				]
			});
		};


});

