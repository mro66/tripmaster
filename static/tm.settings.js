$(function(){

	// Das TabPanel im oberen Teil der ContentBox
	
		var settingsTabPanel = $("#tabPanelContainer").dxTabPanel({
			deferRendering: false,
			height: function() {
				return window.innerHeight - 16;
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
				WebSocket_Send('ResetSector');
				resetSectorForm();
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
				setSectorButton.option("disabled", false);
				setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
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
			onValueChanged: function(data) {
				setSectorButton.option("text", "Etappe: "+getSectorLength()+" km");
			},
		}).dxSelectBox("instance");

		var setSectorButton = $("#button-setsector").dxButton({
			type: "success",
			text: "Etappe einstellen",
			disabled: true,
			onClick: function(data) {
				WebSocket_Send('setSectorLength:'+getSectorLength());
				resetSectorForm();
			},
		}).dxButton("instance");   

		function resetSectorForm() {
			sectorKmSelectBox.reset();
			sector100mSelectBox.reset();
			setSectorButton.option("text", "Etappe einstellen");
			setSectorButton.option("disabled", true);
		};
			
		function getSectorLength() {
			var km_int = parseInt(sectorKmSelectBox.option("value"));
			var km_frac = (sector100mSelectBox.option("value") == null) ? 0 : parseInt(sector100mSelectBox.option("value"));
			var sectorLength = km_int + km_frac/1000;
			return Number.parseFloat(sectorLength).toFixed(1);
		};

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
	
	
	// Footer

		var sectionNumberBox = $("#numberbox-section").dxNumberBox({
			min: -100, max: 100,
			value: 0,
			width: "20%",
		}).dxNumberBox("instance");
	
});

