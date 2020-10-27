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
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

# Konfigurationseditor
config = configparser.RawConfigParser()
# erhält Groß-/Kleinschreibung
config.optionxform = str
configFileName = "/home/pi/tripmaster/tripmaster.ini"
config.read(configFileName)
# aktive Konfiguration
ACTIVE_CONFIG = config.get("Settings", "aktiv")

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
# Messzeitpunkt gesamt und Etappe
T = 0.0
T_SECTOR = 0.0
# Umdrehungen pro Minute
UMIN = 0.0
MS = 0.0
# Anzahl Sensoren
N_SENSORS = 0
# Übersetzung Abtriebswelle - Achswelle (z. B. Differenzial beim Jaguar)
TRANSMISSION_RATIO = 0.0
# Reifenumfang in m
TYRE_SIZE = 0.0
# Liest die Parameter der aktiven Konfiguration
def readConfig():
    global N_SENSORS, TRANSMISSION_RATIO, TYRE_SIZE
    N_SENSORS = config.getint(ACTIVE_CONFIG, "Sensoren")
    TRANSMISSION_RATIO = eval(config.get(ACTIVE_CONFIG, "Übersetzung"))
    TYRE_SIZE = config.getint(ACTIVE_CONFIG, "Radumfang") / 100
    ret = "Konfiguration - " + ACTIVE_CONFIG
    for (each_key, each_val) in config.items(ACTIVE_CONFIG):
        ret += "<br>" + each_key + " - " + each_val
    return ret
readConfig()
# Durchschnittsgeschwindigkeit in Kilometer pro Stunde
AVG_KMH = 0.0
# Vorgegebene  Durchschnittsgeschwindigkeit
AVG_KMH_PRESET = 0.0
# Zurückgelegte Kilometer - gesamt, Rallye und Etappe
KM_TOTAL = 0.0
KM_RALLYE = 0.0
KM_SECTOR = 0.0
# Vorgegebene Etappenlänge
KM_SECTOR_PRESET = 0.0
# Rückwärtszählen beim Verfahren
REVERSE = 1
# Zeitvorgabe der GLP
COUNTDOWN = 0

#-------------------------------------------------------------------

DEBUG = 1
websocketPort = 7070
theMaster = None

#-------------------------------------------------------------------

# Schreibt eine Debug Message in die Tornado Konsole
def printDEBUG(message):
    if DEBUG:
        print(message)

# Schreibt Nachrichten an alle Clients
def messageToAllClients(clients, message):
    for index, client in enumerate(clients):
        if client:
            client.write_message( message )

#-------------------------------------------------------------------
### Parse request from client
#required format-> command:param
def WebRequestHandler(requestlist):
    returnlist = ""
    for request in requestlist:
        request = request.strip()
        requestsplit = request.split(":")
        requestsplit.append("dummy")
        command = requestsplit[0]
        param = requestsplit[1]
        if param == "dummy":
            param = "0"
        if command == "RPM":
            returnlist = getRPM()
        if command == "regTest":
            global COUNTDOWN
            COUNTDOWN -= 1
            returnlist = "{:}".format(COUNTDOWN)
 
    return returnlist

def getRPM():
    global UMIN, T, T_SECTOR, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, REVERSE, AVG_KMH, AVG_KMH_PRESET
    # UMIN ermitteln
    # UMIN = int(UMIN_READER.RPM() + 0.5)
    #... ohne Sensor
    UMIN = 2000 + math.sin((T * 5)/180 * math.pi) * 1000
    # Messzeitpunkt gesamt und Etappe
    T += SAMPLE_TIME
    T_SECTOR += SAMPLE_TIME
    # Geschwindigkeit in Meter pro Sekunde
    MS = UMIN / TRANSMISSION_RATIO / 60 * TYRE_SIZE
    # Geschwindigkeit in Kilometer pro Stunde
    KMH = MS * 3.6
    # Zurückgelegte Kilometer - Gesamt, Rallye und Etappe (Rückwärtszählen beim Umdrehen außer bei Gesamt)
    KM_TOTAL += MS * SAMPLE_TIME / 1000
    KM_RALLYE += MS * SAMPLE_TIME / 1000 * REVERSE
    KM_SECTOR += MS * SAMPLE_TIME / 1000 * REVERSE
    # % zurückgelegte Strecke in der Etappe
    FRAC_SECTOR_DRIVEN = 0
    if KM_SECTOR_PRESET > 0:
        FRAC_SECTOR_DRIVEN = int(min(KM_SECTOR / KM_SECTOR_PRESET * 100, 100))
    # noch zurückzulegende Strecke in der Etappe (mit der 0.005 wird der Wert 0 in der TextCloud vermieden)
    KM_SECTOR_TO_BE_DRIVEN = max(KM_SECTOR_PRESET - KM_SECTOR, 0) #0.005)
        
    if T_SECTOR > 0.0:
        # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde in der Etappe
        AVG_KMH = KM_SECTOR * 1000 / T_SECTOR * 3.6
        # Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
        DEV_AVG_KMH = 0.0
        if AVG_KMH_PRESET > 0.0:
            DEV_AVG_KMH = AVG_KMH - AVG_KMH_PRESET
    return "data:{0:0.1f}:{1:0.1f}:{2:0.1f}:{3:0.1f}:{4:0.2f}:{5:0.2f}:{6:0.2f}:{7:0.2f}:{8:0.2f}:{9:}:{10:0.1f}".format(T, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_TO_BE_DRIVEN, FRAC_SECTOR_DRIVEN, DEV_AVG_KMH)

def startTheMaster(client):
    timed = threading.Timer(SAMPLE_TIME, pushSensorData, [client.wsClients, "RPM", "{:.1f}".format(SAMPLE_TIME)] )
    timed.start()
    timers.append(timed)
    messageToAllClients(client.wsClients, "Tripmaster gestartet!:success:masterStarted")
    messageToAllClients(client.wsClients,"config:" +readConfig())

    
def pushSensorData(clients, what, when):
    what = str(what)
    when = float(when)
    message = WebRequestHandler(what.splitlines());
    messageToAllClients(clients, message)
    timed = threading.Timer( when, pushSensorData, [clients, what, when] )
    timed.start()
    timers.append(timed)

def startRegtest(client):
    timed = threading.Timer(1.0, pushRegtestData, [client.wsClients, "regTest", "1.0"] )
    timed.start()
    timers.append(timed)
    
def pushRegtestData(clients, what, when):
    global AVG_KMH_PRESET
    what = str(what)
    when = float(when)
    message = WebRequestHandler(what.splitlines())
    countdown = int(message)
    if countdown == 0:
        messageToAllClients(clients, "countdown:"+message)
        AVG_KMH_PRESET = 0.0
        messageToAllClients(clients, "GLP gestoppt:success:regTestStopped")
    elif countdown > 0:
        messageToAllClients(clients, "countdown:"+message)
        timed = threading.Timer( when, pushRegtestData, [clients, what, when] )
        timed.start()
        timers.append(timed)

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
            theMaster = self
            startTheMaster(theMaster)
    # the client sent a message
    def on_message(self, message):
        global theMaster, T, T_SECTOR, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, REVERSE, ACTIVE_CONFIG, COUNTDOWN, AVG_KMH_PRESET
        printDEBUG("Message from WebIf: >>>"+message+"<<<")
        # command:param
        message = message.strip()
        messagesplit = message.split(":")
        messagesplit.append("dummyparam")
        command = messagesplit[0]
        param = messagesplit[1]
        if param == "dummy":
            param = "0"

        # Master Start und Pause
        if command == "startMaster":
            if theMaster is None:
                theMaster = self
                startTheMaster(theMaster)
        elif command == "pauseMaster":
            if theMaster is not None:
                for index, timer in enumerate(timers):
                    if timer:
                        timer.cancel()
                theMaster = None
                messageToAllClients(self.wsClients, "Tripmaster pausiert:warning")
        # Etappensteuerung
        elif command == "resetSector":
            T_SECTOR = 0.0
            KM_SECTOR = 0.0
            KM_SECTOR_PRESET = 0.0
            messageToAllClients(self.wsClients, "Etappenzähler auf Null!:success")
        elif command == "setSectorLength":
            KM_SECTOR_PRESET = float(param)
            messageToAllClients(self.wsClients, "Etappe auf "+locale.format("%.2f", KM_SECTOR_PRESET)+" km gesetzt!:success")
        elif command == "toggleReverse":
            REVERSE = REVERSE * -1
            if REVERSE == -1:
                messageToAllClients(self.wsClients, "Verfahren! km-Zähler rückwärts:warning")
            else:
                messageToAllClients(self.wsClients, "km-Zähler wieder normal:success")
        # Gleichmäßigkeitsprüfung
        elif command == "startRegtest":
            COUNTDOWN = int(param)
            startRegtest(self)
            messageToAllClients(self.wsClients, "GLP gestartet:success:regTestStarted")
        elif command == "setAvgSpeed":
            AVG_KMH_PRESET = float(param)
            messageToAllClients(self.wsClients, "avgspeed:" + param)
        elif command == "stopRegtest":
            COUNTDOWN = 0
            AVG_KMH_PRESET = 0.0
            messageToAllClients(self.wsClients, "countdown:0")
            messageToAllClients(self.wsClients, "GLP gestoppt:success:regTestStopped")
        # Einstellungen
        elif command == "resetTripmaster":
            T = 0.0
            KM_TOTAL = 0.0
            KM_RALLYE = 0.0
            KM_SECTOR = 0.0
            KM_SECTOR_PRESET = 0.0
            REVERSE = 1
            messageToAllClients(self.wsClients, "Tripmaster zurückgesetzt!:success")
        elif command == "Konfiguration":
            ACTIVE_CONFIG = param
            config.set("Settings", "aktiv", ACTIVE_CONFIG)
            with open(configFileName, "w") as configfile:    # save
                config.write(configfile)
            self.write_message("config:" +readConfig())
            self.write_message(command + " auf '"+ ACTIVE_CONFIG +"' gesetzt:success")
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
            (r"/(favicon.ico)", StaticHandler, {"path": ""}),
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
            sector_reverse = max(REVERSE, 0),
        )

class SettingsHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        if REVERSE == 1:
            sector_reverse = False
        else:
            sector_reverse = True
        self.render(
            "settings.html",
            debug = DEBUG,
            sample_time = int(SAMPLE_TIME * 1000),
            sector_reverse = sector_reverse,
            
            active_config = ACTIVE_CONFIG,
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
    ws_server = tornado.httpserver.HTTPServer(ws_app, ssl_options={
        "certfile": "/home/pi/tripmaster/certs/servercert.pem",
        "keyfile": "/home/pi/tripmaster/certs/serverkey.pem",
    })
    ws_server.listen(websocketPort)

    web_server = tornado.httpserver.HTTPServer(Web_Application(), ssl_options={
        "certfile": "/home/pi/tripmaster/certs/servercert.pem",
        "keyfile": "/home/pi/tripmaster/certs/serverkey.pem",
    })
    web_server.listen(443)
    tornado.ioloop.IOLoop.instance().start()
except (KeyboardInterrupt, SystemExit):
    for index, timer in enumerate(timers):
        if timer:
            timer.cancel()
    print("\nQuit\n")