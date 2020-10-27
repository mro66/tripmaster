// Initalize the various page elements here...
var pitempTimer;
function init() {
WebSocket_Open();
// start Main Timers
pitempTimer = setInterval(WebSocket_Send, 2000, "PiTEMP");
}
