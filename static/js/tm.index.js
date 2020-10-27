$(function(){

		$("#button-dashboard").dxButton({
			text: "Dashboard",
			icon: "car",
			type: "default",
			visible: true,
			width: "50%",
			onClick: function(e) {
			   location.assign("/dashboard.html");
			 },
		});   
	
		$("#button-settings").dxButton({
			text: "Settings",
			icon: "edit",
			type: "default",
			visible: true,
			width: "50%",
			onClick: function(e) {
			   location.assign("/settings.html");
			 },
		}); 
		
		$("#switch-dashboard").dxSwitch({
		});   
	

});
