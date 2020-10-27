#!/usr/bin/env python3
from __future__ import print_function
import math
import os.path
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import threading

#-------------------------------------------------------------------
# Einstellungen des Tripmasters

# Importe - für VM kommentieren
# import pigpio
# from read_RPM import reader
# import RPi.GPIO as GPIO

# Einrichten der BCM GPIO Nummerierung  - für VM kommentieren
# GPIO.setmode(GPIO.BCM)

# GPIO # des Reedkontakts
REED_GPIO = 14
# Verbindung zu pigpio
pi = None
# Der UMIN_READER
UMIN_READER = None

# Messen alle ... Sekunden
SAMPLE_TIME = 1.0
# Messzeitpunkt
T = 0.0
# Umdrehungen pro Minute
UMIN = 0.0
MS = 0.0
# Reifenumfang
U = 1.2
# Durchschnittsgeschwindigkeit in Kilometer pro Stunde
AVG_KMH = 0.0
# Vorgegebene  Durchschnittsgeschwindigkeit
AVG_KMH_PRESET = 0.0
# Zurückgelegte Kilometer - gesamt und Etappe
KM_TOTAL = 0.0
KM_SECTOR = 0.0
# Vorgegebene Etappenlänge
KM_SECTOR_PRESET = 0.0

#-------------------------------------------------------------------

DEBUG = 1
httpPort = 80
websocketPort = 7070
theMaster = None

#-------------------------------------------------------------------

# Schreibt eine Debug Message in die Tornado Konsole
def printDEBUG(message):
    if DEBUG:
        print(message)

def getRPM():
    global UMIN, T, KM_TOTAL, KM_SECTOR, KM_SECTOR_PRESET, AVG_KMH
    # UMIN ermitteln
    # UMIN = int(UMIN_READER.RPM() + 0.5)
    #... ohne Sensor
    UMIN = 1000 #1000 + math.sin((T * 5)/180 * math.pi) * 1000
    # Messzeitpunkt
    T += SAMPLE_TIME
    # Geschwindigkeit in Meter pro Sekunde
    MS = UMIN / 60 * U
    # Geschwindigkeit in Kilometer pro Stunde
    KMH = MS * 3.6
    # Zurückgelegte Kilometer - gesamt und Etappe
    KM_TOTAL += MS * SAMPLE_TIME / 1000
    KM_SECTOR += MS * SAMPLE_TIME / 1000
    # % zurückgelegte Strecke in der Etappe
    FRAC_SECTOR_DRIVEN = 0
    if KM_SECTOR_PRESET > 0:
        FRAC_SECTOR_DRIVEN = int(min(KM_SECTOR / KM_SECTOR_PRESET * 100, 100))
    # noch zurückzulegende Strecke in der Etappe
    KM_SECTOR_TO_BE_DRIVEN = max(KM_SECTOR_PRESET - KM_SECTOR, 0)
        
    if T > 0.0:
        # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde
        AVG_KMH = KM_TOTAL * 1000 / T * 3.6
    return "data:{0:0.1f}:{1:0.1f}:{2:0.1f}:{3:0.1f}:{4:0.2f}:{5:0.2f}:{6:0.2f}:{7:0.2f}:{8:}".format(T, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_TO_BE_DRIVEN, FRAC_SECTOR_DRIVEN)

#-------------------------------------------------------------------

### Parse request from webif
#required format-> command:value
def WebRequestHandler(requestlist):
    returnlist = ""
    for request in requestlist:
        request = request.strip()
        requestsplit = request.split(':')
        requestsplit.append("dummy")
        command = requestsplit[0]
        value = requestsplit[1]
        if value == "dummy":
            value = "0"

        if command == "RPM":
            returnlist = getRPM()
 
    return returnlist

def pushDataTimed(clients, what, when):
    what = str(what)
    when = float(when)
    message = WebRequestHandler(what.splitlines());
    messageToAllClients(clients, message)
    timed = threading.Timer( when, pushDataTimed, [clients, what, when] )
    timed.start()
    timers.append(timed)

def messageToAllClients(clients, message):
    for index, client in enumerate(clients):
        if client:
            client.write_message( message )
    
### WebSocket server tornado <-> WebInterface
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    # Array der WebSocket Clients
    wsClients = []
    # Client verbunden
    def check_origin(self, origin):
        return True   
    def open(self, page):
        global theMaster, pi, UMIN_READER
        printDEBUG("WebSocket Client verbunden")
        self.stream.set_nodelay(True)
        
        # Jeder WebSocket Client wird dem Array wsClients hinzugefügt
        self.wsClients.append(self)
        if theMaster is None:
            # Verbinden mit pigpio - für VM kommentieren
            # pi = pigpio.pi()
            # UMIN_READER starten - für VM kommentieren
            # UMIN_READER = reader(pi, REED_GPIO)
            timed = threading.Timer(SAMPLE_TIME, pushDataTimed, [self.wsClients, "RPM", "{:.1f}".format(SAMPLE_TIME)] )
            timed.start()
            timers.append(timed)
            theMaster = self
            messageToAllClients(self.wsClients, "Tripmaster gestartet!:success")
    # the client sent the message
    def on_message(self, message):
        global theMaster, KM_SECTOR, KM_SECTOR_PRESET
        printDEBUG("Message from WebIf: >>>"+message+"<<<")
        message = message.strip()
        messagesplit = message.split(':')
        messagesplit.append("dummy")
        command = messagesplit[0]
        value = messagesplit[1]
        if value == "dummy":
            value = "0"

        if command == "ResetSector":
            KM_SECTOR = 0.0
            KM_SECTOR_PRESET = 0.0
            messageToAllClients(self.wsClients, "Etappe zurückgesetzt!:success")
        elif command == "setSectorLength":
            KM_SECTOR_PRESET = float(value)
            messageToAllClients(self.wsClients, "Etappe auf "+value+" km gesetzt!:success")
        elif command == "pauseMaster":
            if theMaster is not None:
                for index, timer in enumerate(timers):
                    if timer:
                        timer.cancel()
                theMaster = None
                messageToAllClients(self.wsClients, "Tripmaster pausiert:warning")
        else:
            self.write_message("Unbekannter Befehl: " + command)
        
    # Client getrennt
    def on_close(self):
        # UMIN_READER stoppen - für VM kommentieren
        # UMIN_READER.cancel()
        # Verbinden mit pigpio - für VM kommentieren
        # pi.stop()
        printDEBUG("WebSocket Client getrennt")
        self.wsClients.remove(self)

#-------------------------------------------------------------------

class Web_Application(tornado.web.Application):
    def __init__(self):
        handlers = [   
              (r"/dashboard.html", DashboardHandler),
              (r"/settings.html", SettingsHandler),
              (r"/static/(.*)", StaticHandler),
              (r'/(favicon.ico)', StaticHandler, {"path": ""}),
          ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=DEBUG,
            autoescape=None
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class DashboardHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        self.render(
            "dashboard.html",
            debug = DEBUG,
            sample_time = int(SAMPLE_TIME * 1000) # "{:.1f}".format(SAMPLE_TIME),
        )

class SettingsHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        self.render(
            "settings.html",
            debug = DEBUG,
            sample_time = int(SAMPLE_TIME * 1000) # "{:.1f}".format(SAMPLE_TIME),
        )

# deliver static files to page
class StaticHandler(tornado.web.RequestHandler):
    def get(self, filename):
        with open("static/" + filename, "r") as fh:
            self.file = fh.read()
        # write to page
        if filename.endswith(".css"):
            self.set_header("Content-Type", "text/css")
        elif filename.endswith(".js"):
            self.set_header("Content-Type", "text/javascript")
        elif filename.endswith(".png"):
            self.set_header("Content-Type", "image/png")
        self.write(self.file) 

try:
    timers = list()
    ws_app = tornado.web.Application([(r"/(.*)", WebSocketHandler),])
    ws_server = tornado.httpserver.HTTPServer(ws_app)
    ws_server.listen(websocketPort)

    web_server = tornado.httpserver.HTTPServer(Web_Application())
    web_server.listen(httpPort)
    tornado.ioloop.IOLoop.instance().start()
except (KeyboardInterrupt, SystemExit):
    for index, timer in enumerate(timers):
        if timer:
            timer.cancel()
    print("\nQuit\n")