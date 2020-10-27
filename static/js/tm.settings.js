var audioElement = document.createElement('audio');
audioElement.setAttribute('src', '/static/Wine_Glass.ogg');
var countdownRunning = false;
    
$(function(){

	// Das TabPanel im oberen Teil der ContentBox
	
		 $("#tabpanel-settings").dxTabPanel({
			deferRendering: false,
			height: "100%",
			loop: true,
			selectedIndex: 0,
			items: [{
				"title": 'Etappe',
				template: $("#tab-sector"),
			}, {
				"title": 'GLP',
				template: $("#tab-regtest"),
			}, {
				"title": 'Setup',
				template: $("#tab-setup"),
			}],
			onSelectionChanged: function(e) {
				if (e.component.option("selectedIndex")==0) {
					$("#textbox-sectorcounter").appendTo("#tab0_sectorcounter");
				} else if (e.component.option("selectedIndex")==2) {
					$("#textbox-sectorcounter").appendTo("#tab2_sectorcounter");
				}
			}
		});

	// tab-sector
        
		$("#button-resetsector").dxButton({
			type: "danger",
			text: "Zurücksetzen",
		    onClick: function(e) {
				// sector1000mNumberbox.reset();
				// sector100mNumberbox.reset();
				$("#lineargauge-kmsector").dxLinearGauge('instance').option("value", 0);
				$("#lineargauge-kmsector").dxLinearGauge('instance').option("subvalues", []);
				sectorPresetTextbox.option("value", "-,-- km");
				sectorCounterTextbox.option("value", formatDistance(0));
				reverseSwitch.option("value", false);
				WebSocket_Send('resetSector');
			},
		}); 
		
		var setSectorButton = $("#button-setsector").dxButton({
			type: "success",
			text: "Vorgabe einstellen",
			disabled: true,
			onClick: function(e) {
				WebSocket_Send('setSectorLength:'+getSectorLength());
				sector1000mNumberbox.reset();
				sector100mNumberbox.reset();
				reverseSwitch.option("value", false);
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

		function getSectorLength() {
			return parseFloat(sector1000mNumberbox.option("value") + 
							  sector100mNumberbox.option("value")/1000).toFixed(2);
		};
		
		function setSectorLength() {
			var sectorLength = getSectorLength();
			if (sectorLength > 0.0) {
				setSectorButton.option("disabled", false);
				setSectorButton.option("text", "Starten");
			} else {
				setSectorButton.option("text", "Vorgabe einstellen");
				setSectorButton.option("disabled", true);
			}
		};
		
        var reverseSwitch = $("#switch-reverse").dxSwitch({
			onValueChanged: function(e) {
				WebSocket_Send("toggleReverse");
				if (e.value === true) {
					// Wenn reverse, dann roter Text
					$("#textbox-sectorcounter").find(".dx-texteditor-input").css("color", "var(--tm-red)");					
				} else {
					$("#textbox-sectorcounter").find(".dx-texteditor-input").css("color", "");					
				}
			},
			onContentReady: function(e) {
				e.component.option("value", (REVERSE === false));
				if (REVERSE === false) {
					$("#textbox-sectorcounter").find(".dx-texteditor-input").css("color", "var(--tm-red)");					
				} else {
					$("#textbox-sectorcounter").find(".dx-texteditor-input").css("color", "");					
				}
			},
        }).dxSwitch("instance");

		// Zwei Spalten Layout
		
		$(".sector-box").dxBox({
			direction: "row",
			width: "100%",
			crossAlign: "start",
		});
	
		var kmSectorLinearGauge = $("#lineargauge-kmsector").dxLinearGauge($.extend(true, {}, linearGaugeOptions, {
		})).dxLinearGauge("instance");
		
		var sectorPresetTextbox = $("#textbox-sectorpreset").dxTextBox($.extend(true, {}, textBoxOptions,{
			value: "0 m",
		})).dxTextBox("instance");

		var sectorCounterTextbox = $("#textbox-sectorcounter").dxTextBox($.extend(true, {}, textBoxOptions,{
			value: formatDistance(0),
			onValueChanged: function(e) {
				if (enableSoundSwitch.option("value")) {
					actValue = unformatDistance(e.value);
					prevValue = unformatDistance(e.previousValue);
					presetValue = unformatDistance(sectorPresetTextbox.option("value"));
					if ((actValue >= presetValue) && (prevValue < presetValue)) {
						// Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
						audioElement.play().catch(function(error) { });
					}
				}
			},
		})).dxTextBox("instance");

	// tab-regtest
	
		var resetRegtestButton = $("#button-resetregtest").dxButton({
			type: "danger",
			text: "Zurücksetzen",
			disabled: true,
		    onClick: function(e) {
				regtestMinuteNumberbox.reset();
				regtestSecondNumberbox.reset();
				regtest1000mNumberbox.reset();
				regtest100mNumberbox.reset();
				// regtestStartHourNumberbox.reset();
				// regtestStartMinuteNumberbox.reset();
				// regtestStartSecondNumberbox.reset();
			},
		}).dxButton("instance"); 
		
		var setRegtestButton = $("#button-setregtest").dxButton({
			type: "success",
			text: "Vorgaben einstellen",
			disabled: true,
			onClick: function(e) {
				if (countdownRunning == false) {
					WebSocket_Send('startRegtest:'+getRegtestTime());
					countdownRunning = true;
					e.component.option("text", "Stoppen");
					resetRegtestButton.option("disabled", true);
					$("#textbox-regtestseconds").find(".dx-texteditor-input").css("color", "var(--tm-red)");
				} else {
					WebSocket_Send('stopRegtest');
					resetRegtest();
					var texteditorInput = document.getElementById("textbox-regtestseconds").children[0].children[0];
					texteditorInput.classList.remove("flicker");
					texteditorInput.classList.remove("secondyellow");
					texteditorInput.classList.remove("secondred");
					texteditorInput.style.color = "black";
				}				
			},
		}).dxButton("instance");

		function resetRegtest() {
			countdownRunning = false;
			regtestMinuteNumberbox.reset();
			regtestSecondNumberbox.reset();
		};


	// Zeitvorgabe
		
		var regtestMinuteNumberbox = $("#numberbox-regtestminute").dxNumberBox({
			min: 0, max: 10,
			value: 0,
			format: "#0 min",
			showSpinButtons: true,
			useLargeSpinButtons: true,
			onValueChanged: function (e) {
				setRegtestTime();
				if (e.value == null) {
					e.component.option("value", 0);
				}					
			},
		}).dxNumberBox("instance");
			
		var regtestSecondNumberbox = $("#numberbox-regtestsecond").dxNumberBox({
			min: -1, max: 60,
			value: 0,
			step: 1,
			format: "#0 s",
			showSpinButtons: true,
			useLargeSpinButtons: true,
			onValueChanged: function (e) {
				setRegtestTime();
				if (e.value == e.component.option("max")) {
					e.component.option("value", 0);
					regtestMinuteNumberbox.option("value", regtestMinuteNumberbox.option("value")+1);
				} else if (e.value == e.component.option("min")) {
					if (getRegtestTime() > 0) {
						e.component.option("value", e.component.option("max")-e.component.option("step"));
						regtestMinuteNumberbox.option("value", regtestMinuteNumberbox.option("value")-1);
					} else {
						e.component.option("value", 0);
					}
				} else if (e.value == null) {
					e.component.option("value", 0);
				}					
			},		
		}).dxNumberBox("instance");

		function getRegtestTime() {
			return parseInt(regtestMinuteNumberbox.option("value")*60 + regtestSecondNumberbox.option("value"))
		};

		function setRegtestTime() {
			var regtestTime = getRegtestTime();
			regtestSecondsTextbox.option("value", regtestTime + " sek");
			if (regtestTime > 0) {
				resetRegtestButton.option("disabled", false);
				setRegtestButton.option("disabled", false);
				setRegtestStartTime();
			} else {
				resetRegtestButton.option("disabled", true);
				setRegtestButton.option("disabled", true);
				setRegtestButton.option("text", "Vorgaben einstellen");
			}
			setRegtestAvgSpeed();
		};

		// Strecke
	
		var regtest1000mNumberbox = $("#numberbox-regtest1000m").dxNumberBox({
			min: 0, max: 12,
			value: 0,
			format: "#0 km",
			showSpinButtons: true,
			useLargeSpinButtons: true,
			onValueChanged: function (e) {
				setRegtestLength();
				if (e.value == null) {
					e.component.option("value", 0);
				}					
			},
		}).dxNumberBox("instance");
			
		var regtest100mNumberbox = $("#numberbox-regtest100m").dxNumberBox({
			min: -1, max: 1000,
			value: 0,
			step: 10,
			format: "#0 m",
			showSpinButtons: true,
			useLargeSpinButtons: true,
			onValueChanged: function (e) {
				setRegtestLength();
				if (e.value == e.component.option("max")) {
					e.component.option("value", 0);
					regtest1000mNumberbox.option("value", regtest1000mNumberbox.option("value")+1);
				} else if (e.value == e.component.option("min")) {
					if (getRegtestLength() > 0) {
						e.component.option("value", e.component.option("max")-e.component.option("step"));
						regtest1000mNumberbox.option("value", regtest1000mNumberbox.option("value")-1);
					} else {
						e.component.option("value", 0);
					}
				} else if (e.value == null) {
					e.component.option("value", 0);
				}					
			},		
		}).dxNumberBox("instance");

		function getRegtestLength() {
			return parseFloat(regtest1000mNumberbox.option("value") + 
							  regtest100mNumberbox.option("value")/1000).toFixed(2);
		};
		
		function setRegtestLength() {
			var regtestLength = getRegtestLength();
			regtestLengthTextbox.option("value", formatDistance(regtestLength));
			setRegtestAvgSpeed();
		};

		//Startzeit (TODO: nicht fertig implementiert)
		
		var regtestStartHourNumberbox = $("#numberbox-regteststarthour").dxNumberBox({
			min: -1, max: 24,
			value: 0,
			step: 1,
			format: "#0 h",
			showSpinButtons: true,
			useLargeSpinButtons: false,
			onValueChanged: function (e) {
				if (e.value == e.component.option("max")) {
					e.component.option("value", 0);
				} else if (e.value == e.component.option("min")) {
					e.component.option("value", e.component.option("max")-e.component.option("step"));
				} else if (e.value == null) {
					e.component.option("value", 0);
				}
				setRegtestStartTime();
			},
		}).dxNumberBox("instance");
			
		var regtestStartMinuteNumberbox = $("#numberbox-regteststartminute").dxNumberBox({
			min: -1, max: 60,
			value: 0,
			step: 1,
			format: "#0 min",
			showSpinButtons: true,
			useLargeSpinButtons: false,
			onValueChanged: function (e) {
				if (e.value == e.component.option("max")) {
					e.component.option("value", 0);
					regtestStartHourNumberbox.option("value", regtestStartHourNumberbox.option("value")+1);
				} else if (e.value == e.component.option("min")) {
					e.component.option("value", e.component.option("max")-e.component.option("step"));
					regtestStartHourNumberbox.option("value", regtestStartHourNumberbox.option("value")-1);
				} else if (e.value == null) {
					e.component.option("value", 0);
				}					
				setRegtestStartTime();
			},
		}).dxNumberBox("instance");
			
		var regtestStartSecondNumberbox = $("#numberbox-regteststartsecond").dxNumberBox({
			min: -1, max: 60,
			value: 0,
			step: 1,
			format: "#0 s",
			showSpinButtons: true,
			useLargeSpinButtons: false,
			onValueChanged: function (e) {
				if (e.value == e.component.option("max")) {
					e.component.option("value", 0);
					regtestStartMinuteNumberbox.option("value", regtestStartMinuteNumberbox.option("value")+1);
				} else if (e.value == e.component.option("min")) {
					e.component.option("value", e.component.option("max")-e.component.option("step"));
					regtestStartMinuteNumberbox.option("value", regtestStartMinuteNumberbox.option("value")-1);
				} else if (e.value == null) {
					e.component.option("value", 0);
				}					
				setRegtestStartTime();
			},		
		}).dxNumberBox("instance");

		function getRegtestStartTime() {
			var startHour = regtestStartHourNumberbox.option("value");
			var startMinute = regtestStartMinuteNumberbox.option("value");
			var startSecond = regtestStartSecondNumberbox.option("value");
			if ((startHour + startMinute + startSecond) > 0) {
				var startDate = new Date(); 
				startDate.setHours  (startHour);
				startDate.setMinutes(startMinute);
				startDate.setSeconds(startSecond);
				return startDate;
			} else {
				return 0;
			};
		};			

		function setRegtestStartTime() {
			if (setRegtestButton.option("disabled") == false) {
				startDate = 0; //getRegtestStartTime();
				if (startDate > 0) {
					setRegtestButton.option("text", "Um "+startDate.toTimeString().split(' ')[0]+" starten");	
				} else {
					setRegtestButton.option("text", "Starten"); //"Manuell starten");
				};
			};
		};			

		// Anzeige
		
		var regtestSecondsTextbox = $("#textbox-regtestseconds").dxTextBox($.extend(true, {}, textBoxOptions,{
			value: "0 sek",
			onValueChanged: function(e) {
				// var texteditorInput = $("#textbox-regtestseconds").find(".dx-texteditor-input");
				var texteditorInput = document.getElementById("textbox-regtestseconds").children[0].children[0];
				var myValue = parseInt(e.value);
				regtestMinutesTextbox.option("value", formatNumber(myValue/60) + " min");
				if (countdownRunning == true) {
					if (myValue > 0) {
						animationClass = "secondyellow";
						texteditorInput.style.color = "var(--tm-red)";
						if (myValue <= 10) {
							if (myValue <= 5) {
								animationClass = "secondred";
							};
							texteditorInput.classList.remove("flicker");
							texteditorInput.classList.remove(animationClass);
							void texteditorInput.offsetWidth;
							texteditorInput.classList.add(animationClass);
						};
					} else {
						if (enableSoundSwitch.option("value")) {
							// Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
							audioElement.play().catch(function(error) { });
						};
						texteditorInput.classList.remove("flicker");
						texteditorInput.classList.remove("secondyellow", "secondred");
						void texteditorInput.offsetWidth;
						texteditorInput.classList.add("flicker");
						texteditorInput.style.color = "black";
						resetRegtest();
					}
				};
			},
		})).dxTextBox("instance");
		
		var regtestMinutesTextbox = $("#textbox-regtestminutes").dxTextBox($.extend(true, {}, textBoxOptions,{
			value: "0,00 min",
		})).dxTextBox("instance");
		
		var regtestLengthTextbox = $("#textbox-regtestlength").dxTextBox($.extend(true, {}, textBoxOptions,{
			value: "0,00 km",
		})).dxTextBox("instance");
				
		var regtestAvgSpeedTextbox = $("#textbox-regtestavgspeed").dxTextBox($.extend(true, {}, textBoxOptions,{
			value: "--,-- kmh",
		})).dxTextBox("instance");
		
		function setRegtestAvgSpeed() {
			var regtestLength = getRegtestLength();
			var regtestTime = getRegtestTime();
			if ((regtestLength > 0) && (regtestTime > 0)) {
				regtestAvgSpeedTextbox.option("value", formatNumber(regtestLength / regtestTime * 60 * 60) + " kmh");
			} else {
				regtestAvgSpeedTextbox.option("value", "--,-- kmh");
			}
		};

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

        var enableSoundSwitch = $("#switch-enablesound").dxSwitch({
            value: false,
			onValueChanged: function(e) {
                if (e.value === true) {
                    // Wenn nicht vom User aktiviert, wird "Uncaught (in promise) DOMException" geworfen
                    audioElement.play().catch(function(error) { });
                } 
			},
        }).dxSwitch("instance");
        
		var tyreSizeNumberBox = $("#numberbox-tyresize").dxNumberBox({
			min: 0, max: 200,
			value: TYRE_SIZE,
			format: "#0 cm",
			width: "70%",
			onFocusIn: function (e) {
				setTyreSizeButton.option("disabled", false);
			},
		}).dxNumberBox("instance");
		
		var setTyreSizeButton = $("#button-settyresize").dxButton({
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
			onClick: function(e) {
				confirmDialogResetTripmaster().show().done(function (dialogResult) {
					if (dialogResult) {
						WebSocket_Send('resetTripmaster');
						rallyeCounterTextbox.option("value", formatDistance(0));
						totalCounterTextbox.option("value", formatDistance(0));
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

		var rallyeCounterTextbox = $("#textbox-rallyecounter").dxTextBox($.extend(true, {}, textBoxOptions,{
		})).dxTextBox("instance");
		
		var totalCounterTextbox = $("#textbox-totalcounter").dxTextBox($.extend(true, {}, textBoxOptions,{
		})).dxTextBox("instance");
		
});
