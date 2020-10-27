#!/usr/bin/env python3
from __future__ import print_function
import configparser
import locale
import math
import os.path
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import threading

#-------------------------------------------------------------------
# Einstellungen des Tripmasters
# Komma als Dezimaltrennzeichen
locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

# Konfigurationseditor
config = configparser.RawConfigParser()
# erhält Groß-/Kleinschreibung
config.optionxform = str
configFileName = "/home/pi/tripmaster/tripmaster.ini"
config.read(configFileName)
# alle gespeicherten Parameter
parameters = dict(config.items('Settings'))

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
TYRE_SIZE = config.getint("Settings", "Radumfang") / 100
# Durchschnittsgeschwindigkeit in Kilometer pro Stunde
AVG_KMH = 0.0
# Vorgegebene  Durchschnittsgeschwindigkeit
AVG_KMH_PRESET = 0.0
# Zurückgelegte Kilometer - gesamt und Abschnitt
KM_TOTAL = 0.0
KM_SECTOR = 0.0
# Vorgegebene Abschnittlänge
KM_SECTOR_PRESET = 0.0
# Rückwärtszählen beim Verfahren
SECTOR_REVERSE = 1

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
    global UMIN, T, KM_TOTAL, KM_SECTOR, KM_SECTOR_PRESET, SECTOR_REVERSE, AVG_KMH
    # UMIN ermitteln
    # UMIN = int(UMIN_READER.RPM() + 0.5)
    #... ohne Sensor
    UMIN = 1000 + math.sin((T * 5)/180 * math.pi) * 1000
    # Messzeitpunkt
    T += SAMPLE_TIME
    # Geschwindigkeit in Meter pro Sekunde
    MS = UMIN / 60 * TYRE_SIZE
    # Geschwindigkeit in Kilometer pro Stunde
    KMH = MS * 3.6
    # Zurückgelegte Kilometer - gesamt und Abschnitt (Rückwärtszählen beim Umdrehen)
    KM_TOTAL += MS * SAMPLE_TIME / 1000
    KM_SECTOR += MS * SAMPLE_TIME / 1000 * SECTOR_REVERSE
    # % zurückgelegte Strecke im Abschnitt
    FRAC_SECTOR_DRIVEN = 0
    if KM_SECTOR_PRESET > 0:
        FRAC_SECTOR_DRIVEN = int(min(KM_SECTOR / KM_SECTOR_PRESET * 100, 100))
    # noch zurückzulegende Strecke im Abschnitt (mit der 0.005 wird der Wert 0 in der TextCloud vermieden)
    KM_SECTOR_TO_BE_DRIVEN = max(KM_SECTOR_PRESET - KM_SECTOR, 0) #0.005)
        
    if T > 0.0:
        # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde
        AVG_KMH = KM_TOTAL * 1000 / T * 3.6
    return "data:{0:0.1f}:{1:0.1f}:{2:0.1f}:{3:0.1f}:{4:0.2f}:{5:0.2f}:{6:0.2f}:{7:0.2f}:{8:}".format(T, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_TO_BE_DRIVEN, FRAC_SECTOR_DRIVEN)

#-------------------------------------------------------------------

### Parse request from client
#required format-> command:param
def WebRequestHandler(requestlist):
    returnlist = ""
    for request in requestlist:
        request = request.strip()
        requestsplit = request.split(':')
        requestsplit.append("dummy")
        command = requestsplit[0]
        param = requestsplit[1]
        if param == "dummy":
            param = "0"

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

def startTheMaster(client):
    global theMaster, pi, UMIN_READER
    if theMaster is None:
        timed = threading.Timer(SAMPLE_TIME, pushDataTimed, [client.wsClients, "RPM", "{:.1f}".format(SAMPLE_TIME)] )
        timed.start()
        timers.append(timed)
        theMaster = client
        messageToAllClients(client.wsClients, "Tripmaster gestartet!:success")
    
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
            startTheMaster(self)
    # the client sent a message
    def on_message(self, message):
        global theMaster, T, KM_TOTAL, KM_SECTOR, KM_SECTOR_PRESET, SECTOR_REVERSE, TYRE_SIZE
        printDEBUG("Message from WebIf: >>>"+message+"<<<")
        # command:param
        message = message.strip()
        messagesplit = message.split(':')
        messagesplit.append("dummyparam")
        command = messagesplit[0]
        param = messagesplit[1]
        if param == "dummy":
            param = "0"

        # Master Start und Pause
        if command == "startMaster":
            startTheMaster(self)
        elif command == "pauseMaster":
            if theMaster is not None:
                for index, timer in enumerate(timers):
                    if timer:
                        timer.cancel()
                theMaster = None
                messageToAllClients(self.wsClients, "Tripmaster pausiert:warning")
        # Abschnittsteuerung
        elif command == "resetSector":
            KM_SECTOR = 0.0
            KM_SECTOR_PRESET = 0.0
            messageToAllClients(self.wsClients, "Abschnittzähler auf Null!:success")
        elif command == "setSectorLength":
            KM_SECTOR_PRESET = float(param)
            messageToAllClients(self.wsClients, "Abschnitt auf "+locale.format("%.2f", KM_SECTOR_PRESET)+" km gesetzt!:success")
        elif command == "toggleSectorReverse":
            SECTOR_REVERSE = SECTOR_REVERSE * -1
            if SECTOR_REVERSE == -1:
                messageToAllClients(self.wsClients, "Verfahren! Abschnittzähler rückwärts:warning")
            else:
                messageToAllClients(self.wsClients, "Abschnittzähler wieder normal:success")
        # Abschnittsteuerung
        elif command == "resetTripmaster":
            T = 0.0
            KM_TOTAL = 0.0
            KM_SECTOR = 0.0
            KM_SECTOR_PRESET = 0.0
            SECTOR_REVERSE = 1
            messageToAllClients(self.wsClients, "Tripmaster zurückgesetzt!:success")
        # Parameterverwaltung
        elif command in parameters:
            config.set("Settings", command, param)
            if command == "Radumfang":
                TYRE_SIZE = int(param)/100
            with open(configFileName, 'w') as configfile:    # save
                config.write(configfile)
            self.write_message(command + " auf '"+ param +"' gesetzt:success")
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
            (r"/", IndexHandler),
            (r"/dashboard.html", DashboardHandler),
            (r"/settings.html", SettingsHandler),
            (r"/static/(.*)", StaticHandler),
            (r"/static/js/(.*)", StaticHandler),
            (r'/(favicon.ico)', StaticHandler, {"path": ""}),
          ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=DEBUG,
            autoescape=None
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class IndexHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        self.render(
            "index.html"
        )

class DashboardHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        self.render(
            "dashboard.html",
            debug = DEBUG,
            sample_time = int(SAMPLE_TIME * 1000),
            sector_reverse = max(SECTOR_REVERSE, 0),
        )

class SettingsHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        if SECTOR_REVERSE == 1:
            sector_reverse = False
        else:
            sector_reverse = True
        self.render(
            "settings.html",
            debug = DEBUG,
            sample_time = int(SAMPLE_TIME * 1000),
            sector_reverse = sector_reverse,
            
            tyre_size = config.get("Settings", "Radumfang"),
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
        if filename.endswith(".json"):
            self.set_header("Content-Type", "application/json")
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