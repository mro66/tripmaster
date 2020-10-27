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
		}).dxTabPanel("instance");

	// Tab etappeTab

		var resetSectorButton = $("#button-resetsector").dxButton({
			type: "danger",
			text: "RESET",
		    onClick: function(data) {
				WebSocket_Send('resetSector');
				sectorPresetTextBox.reset();
				sectorKmSelectBox.reset();
				sector100mSelectBox.reset();
				sectorReverseSwitch.reset();
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
			width: "50%",
			elementAttr: {
					style: "float: left"
				},
			onValueChanged: function(data) {
				if (getSectorLength() > 0.0) {
					setSectorButton.option("disabled", false);
					setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
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
			width: "50%",
			elementAttr: {
				style: "float: left"
			},
			onValueChanged: function(e) {
				if (getSectorLength() > 0.0) {
					setSectorButton.option("disabled", false);
					setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
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
			onClick: function(data) {
				WebSocket_Send('setSectorLength:'+getSectorLength());
				sectorKmSelectBox.reset();
				sector100mSelectBox.reset();
				sectorReverseSwitch.reset();
			},
		}).dxButton("instance");   

		function getSectorLength() {
			var km_int = (sectorKmSelectBox.option("value") == null) ? 0 : parseInt(sectorKmSelectBox.option("value"));
			var km_frac = (sector100mSelectBox.option("value") == null) ? 0 : parseInt(sector100mSelectBox.option("value"));
			var sectorLength = km_int + km_frac/1000;
			return Number.parseFloat(sectorLength).toFixed(1);
		};

		// Zwei Spalten Layout
		
		$(".box-twocolumn").dxBox({
			direction: "row",
			width: "100%",
			crossAlign: "start",
		});
	
		var sectorPresetTextBox = $("#textbox-sectorpreset").dxTextBox({
			value: "0.0 km",
			readOnly: true,
			width: 110,
		}).dxTextBox("instance");

		var sectorTextBox = $("#textbox-sector").dxTextBox({
			value: "",
			readOnly: true,
			width: 110,
		}).dxTextBox("instance");

		var sectorReverseSwitch = $("#switch-sectorreverse").dxSwitch({
			switchedOffText: "Nein",
			switchedOnText: "Ja",
			width: 110,
			value: SECTOR_REVERSE,
			onValueChanged: function(e) {
				WebSocket_Send("toggleSectorReverse");
				if (e.value == false) {
					sectorTextBox.option("elementAttr.style", "border: 1px #f4f4f4 solid")
				} else {
					sectorTextBox.option("elementAttr.style", "border: 1px #d9534f solid")						
				}
			},
			onInitialized: function(e) {
				if (!SECTOR_REVERSE) {
					sectorTextBox.option("elementAttr.style", "border: 1px #f4f4f4 solid")
				} else {
					sectorTextBox.option("elementAttr.style", "border: 1px #d9534f solid")						
				}
			},
		}).dxSwitch("instance");
		
		$("#radio-group-sectorreverse").dxRadioGroup({
			items: yesno,
			value: yesno[1],
			layout: "horizontal"
		});

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
			width: "50%",
			elementAttr: {
					style: "float: left"
				},
			onValueChanged: function(data) {
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
			width: "50%",
			elementAttr: {
				style: "float: left"
			},
			onValueChanged: function(data) {
				//setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
			},
		}).dxSelectBox("instance");

	// Tab Setup

		$("#radio-group-stoptripmaster").dxRadioGroup({
			items: yesno,
			value: yesno[0],
			layout: "horizontal"
		});
});

var yesno = ["ja", "nein"];
var onoff = ["an", "aus"];
var plusminus = ["+", "-"];