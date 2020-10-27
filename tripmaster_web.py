#!/usr/bin/env python3

from __future__ import print_function
from datetime import datetime
from logging.handlers import RotatingFileHandler
from tornado.options import options
import configparser
import gpsd
import io
import locale
import logging
import math
import os.path
import pytz
import simplekml
import subprocess
import sys
import threading    
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop

#-------------------------------------------------------------------
# Einstellungen des Tripmasters
# Komma als Dezimaltrennzeichen
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
# Zeitzonen
tz_utc = pytz.timezone('UTC')
tz_berlin = pytz.timezone('Europe/Berlin')  

# Dateiausgaben
# Programmpfad
tripmasterPath = os.path.dirname(os.path.abspath(__file__))

# Loggereinstellungen
logging.basicConfig(filename = tripmasterPath+"/out/tripmaster.log", format="%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s", datefmt="%d.%m.%Y %H:%M:%S", level=logging.WARNING)

logger = logging.getLogger('Tripmaster')
logger.setLevel(logging.DEBUG)
logger.debug("Tornado gestartet")

# class StreamToLog(io.IOBase):
    # def write(self, s):
        # error = True
        # if not s == "\n":
            # if error:
                # logger.error(s.strip())
            # else:
                # logger.info(s)

# sys.stderr = StreamToLog()
# sys.stdout = StreamToLog()

# Geodatenausgabe als KML und/oder CSV
kml = simplekml.Kml()

TRACK_RED = simplekml.Style()
TRACK_RED.linestyle.width = 5
TRACK_RED.linestyle.color = "ff4f53d9"

TRACK_GREEN = simplekml.Style()
TRACK_GREEN.linestyle.width = 5
TRACK_GREEN.linestyle.color = "ff5cb85c"

SECTORTRACK = kml.newmultigeometry(name="Sektor 1")
SECTORTRACK.style = TRACK_GREEN
SECTORTRACK_LINE = SECTORTRACK.newlinestring()

ROUNDABOUTS = kml.newmultigeometry() # Jeder Punkt als Teil _einer_ MultiGeometry
ROUNDABOUTS.style.iconstyle.icon.href = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Zeichen_215_-_Kreisverkehr%2C_StVO_2000.svg/200px-Zeichen_215_-_Kreisverkehr%2C_StVO_2000.svg.png"

kmlFile = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.kml".format(datetime.now());
csvFile = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.csv".format(datetime.now());

TRACK_NO = 1
IS_NEW_TRACK = False


# Konfigurationseditor
config = configparser.RawConfigParser()
# erhält Groß-/Kleinschreibung
config.optionxform = str
configFileName = tripmasterPath+"/tripmaster.ini"
config.read(configFileName)
# aktive Konfiguration
ACTIVE_CONFIG = config.get("Settings", "aktiv")

# Gestartet?
IS_STARTED = False
# Zeichnet auf?
IS_RECORDING = False
# Hat Antriebswellensensor?
HAS_SENSORS = False
# Zeit ist synchronisiert?
IS_TIME_SYNC = False

# Importe - für VM kommentieren
import pigpio
from read_RPM import reader
import RPi.GPIO as GPIO
# Einrichten der BCM GPIO Nummerierung - für VM kommentieren
GPIO.setmode(GPIO.BCM)
# GPIO Pins der Sensoren
GPIO_PIN_1 = 17 # weiß
GPIO_PIN_2 = 18 # blau
# Setup als input
GPIO.setup(GPIO_PIN_1, GPIO.IN)
GPIO.setup(GPIO_PIN_2, GPIO.IN)

# Verbindung zu pigpio
pi = None
# Die UMIN_READER
UMIN_READER_1 = None
UMIN_READER_2 = None
# Impulse pro Umdrehung
PULSES_PER_REV = 1.0

# Verbindung zum GPS Deamon
gpsd.connect()

# index
INDEX = 0
# Messen alle ... Sekunden
SAMPLE_TIME = 1.0
# Messzeitpunkt gesamt und Sektor
T = 0.0
T_SECTOR = 0.0

# Anzahl Sensoren
N_SENSORS = 1
# Übersetzung Abtriebswelle - Achswelle (z. B. Differenzial beim Jaguar)
TRANSMISSION_RATIO = 1.0
# Reifenumfang in m
TYRE_SIZE = 2.0
# Liest die Parameter der aktiven Konfiguration
def setConfig():
    global N_SENSORS, TRANSMISSION_RATIO, TYRE_SIZE
    N_SENSORS = config.getint(ACTIVE_CONFIG, "Sensoren")
    TRANSMISSION_RATIO = eval(config.get(ACTIVE_CONFIG, "Übersetzung"))
    TYRE_SIZE = config.getint(ACTIVE_CONFIG, "Radumfang") / 100
    
setConfig()

def getConfig():
    ret = ''
    for (each_key, each_val) in config.items(ACTIVE_CONFIG):
        ret += each_key + "=" + each_val + "&"
    # das letzte Zeichen löschen
    return ret[:-1]

# Durchschnittsgeschwindigkeit in Kilometer pro Stunde
AVG_KMH = 0.0
# Vorgegebene  Durchschnittsgeschwindigkeit
AVG_KMH_PRESET = 0.0
# Zurückgelegte Kilometer - gesamt, Rallye und Sektor
KM_TOTAL = 0.0
KM_RALLYE = 0.0
KM_SECTOR = 0.0
LAT_PREV = None
LON_PREV = None
KM_TOTAL_GPS = 0.0
KM_RALLYE_GPS = 0.0
KM_SECTOR_GPS = 0.0
# Vorgegebene Sektorenlänge
KM_SECTOR_PRESET = 0.0
# Rückwärtszählen beim Verfahren
REVERSE = 1
# Zeitvorgabe der GLP
COUNTDOWN = 0

#-------------------------------------------------------------------

DEBUG = 1
websocketPort = 7070

#-------------------------------------------------------------------

# Schreibt Nachrichten an alle Clients
def messageToAllClients(clients, message):
    for index, client in enumerate(clients):
        if client:
            client.write_message(message)

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
        if command == "getData":
            returnlist = getData()
        if command == "regTest":
            global COUNTDOWN
            COUNTDOWN -= 1
            returnlist = "{:}".format(COUNTDOWN)
 
    return returnlist

def syncTime(GPS_CURRENT):
    global IS_TIME_SYNC
    if (len(GPS_CURRENT.time) == 24):
        naive = datetime.strptime(GPS_CURRENT.time, '%Y-%m-%dT%H:%M:%S.%fZ')
        utc = tz_utc.localize(naive)
        local = utc.astimezone(tz_berlin)
        subprocess.call("sudo date -u -s '"+str(local)+"' > /dev/null 2>&1", shell=True)
        IS_TIME_SYNC = True

def getData():
    global HAS_SENSORS, N_SENSORS, INDEX, T_SECTOR, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, REVERSE, AVG_KMH, AVG_KMH_PRESET
    global KM_TOTAL_GPS, KM_RALLYE_GPS, KM_SECTOR_GPS, LAT_PREV, LON_PREV
    global kml, SECTORTRACK, SECTORTRACK_LINE, TRACK_NO, IS_NEW_TRACK
    
    # Ein 0 V Potential an einem der GPIO Pins aktiviert die Antriebswellensensoren
    if ((GPIO.input(GPIO_PIN_1) == 0) or (GPIO.input(GPIO_PIN_2) == 0)) and not HAS_SENSORS:
        HAS_SENSORS = True
        logger.debug("Antriebswellensensor(en) automatisch aktiviert!")
        
    # Index hochzählen
    INDEX += 1
    # Geschwindigkeit in Kilometer pro Stunde
    KMH = 0.0

    #GPS
    
    # Aktuelle Position
    GPS_CURRENT = gpsd.get_current()
    # Aktuelle Zeit
    TIME = datetime.now()
    
    # Alle 10 Durchläufe Zeit synchronisieren
    if (INDEX % 10 == 0) or (IS_TIME_SYNC == False):
        syncTime(GPS_CURRENT) 

    # Gefahrene Distanz in km (berechnet aus Geokoordinaten)
    DIST = 0.0
    
    # Ein 3D Fix ist notwendig, sonst zu ungenau
    if GPS_CURRENT.mode >= 2:

        # KMH_GPS = GPS_CURRENT.speed() * 3.6 - gibt auf einmal nur noch 0.0 zurück
        if (GPS_CURRENT.hspeed > 1.0) and IS_RECORDING:
            KMH = GPS_CURRENT.hspeed * 3.6

        KMH_GPS = KMH

        # DEBUG - Start
        # LAT = GPS_CURRENT.lat
        # LON = GPS_CURRENT.lon
        KMH_GPS = 0.1
        LAT = GPS_CURRENT.lat + INDEX/5000
        LON = GPS_CURRENT.lon + INDEX/5000
        # DEBUG - Ende
        
        if (LAT_PREV is not None) and (LON_PREV is not None) and (KMH_GPS > 0.0) and IS_RECORDING:
            DIST = calcGPSdistance(LAT_PREV, LAT, LON_PREV, LON)

        # DEBUG - Start
        if IS_RECORDING:
            MS = DIST * 1000
            KMH_GPS = MS * 3.6
            KMH = KMH_GPS
        # DEBUG - Ende
            
        LAT_PREV = LAT
        LON_PREV = LON
        KM_TOTAL += DIST
        KM_TOTAL_GPS = KM_TOTAL
        KM_RALLYE += DIST * REVERSE
        KM_RALLYE_GPS = KM_RALLYE
        KM_SECTOR += DIST * REVERSE
        KM_SECTOR_GPS = KM_SECTOR
    else:
        KMH_GPS = 0.0
        LAT = 0.0
        LON = 0.0

    # Antriebswellensensor(en)

    # Umdrehungen der Antriebswelle(n) pro Minute
    UMIN = 0.0

    if HAS_SENSORS:
    
        # UMIN ermitteln - für VM kommentieren
        UMIN = int(UMIN_READER_1.RPM() + 0.5)
        if N_SENSORS > 1:
            UMIN += int(UMIN_READER_2.RPM() + 0.5)
            UMIN = UMIN / 2    
        #... ohne Sensor
        # UMIN = 2000 + math.sin((T * 5)/180 * math.pi) * 1000
        # Geschwindigkeit in Meter pro Sekunde
        if IS_RECORDING:
            MS = UMIN / TRANSMISSION_RATIO / 60 * TYRE_SIZE
        
        # Geschwindigkeit in Kilometer pro Stunde
        KMH = MS * 3.6
        # Zurückgelegte Kilometer - Gesamt, Rallye und Sektor (Rückwärtszählen beim Umdrehen außer bei Gesamt)
        KM_TOTAL += MS * SAMPLE_TIME / 1000
        KM_RALLYE += MS * SAMPLE_TIME / 1000 * REVERSE
        KM_SECTOR += MS * SAMPLE_TIME / 1000 * REVERSE

    # Messzeitpunkte Sektor
    if IS_RECORDING:
        T_SECTOR += SAMPLE_TIME

    # % zurückgelegte Strecke in der Sektor
    FRAC_SECTOR_DRIVEN = 0
    if KM_SECTOR_PRESET > 0:
        FRAC_SECTOR_DRIVEN = int(min(KM_SECTOR / KM_SECTOR_PRESET * 100, 100))
    # noch zurückzulegende Strecke in der Sektor (mit der 0.005 wird der Wert 0 in der TextCloud vermieden)
    KM_SECTOR_PRESET_REST = max(KM_SECTOR_PRESET - KM_SECTOR, 0) #0.005)
        
    # Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
    DEV_AVG_KMH = 0.0
    
    if T_SECTOR > 0.0:
        # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde im Sektor
        AVG_KMH = KM_SECTOR * 1000 / T_SECTOR * 3.6
        if AVG_KMH_PRESET > 0.0:
            DEV_AVG_KMH = AVG_KMH - AVG_KMH_PRESET
    
    if IS_RECORDING:
        if IS_NEW_TRACK:
            TRACK_NO += 1
            SECTORTRACK_LINE.coords.addcoordinates([(LON,LAT)])
            kml.save(kmlFile)
            SECTORTRACK = kml.newmultigeometry(name="Sektor "+str(TRACK_NO))
            SECTORTRACK_LINE = SECTORTRACK.newlinestring()
            if (TRACK_NO % 2 == 0):
                SECTORTRACK.style = TRACK_RED
            else:
                SECTORTRACK.style = TRACK_GREEN
            SECTORTRACK_LINE.coords.addcoordinates([(LON,LAT)])
            kml.save(kmlFile)
            IS_NEW_TRACK = False
        
        # Alle 5 Durchläufe Geodaten abspeichern
        # Bounding Box von Deutschland: (5.98865807458, 47.3024876979, 15.0169958839, 54.983104153)),
        if (INDEX % 5 == 0) and IS_TIME_SYNC and 15.1 > LON > 5.9 and 55.0 > LAT > 47.3:    
            # geostring = "{0:%d.%m.%Y %H:%M:%S};{1:};{2:};{3:0.1f};{4:0.2f};{5:0.2f};{6:0.2f};{7:0.1f};{8:0.2f};{9:0.2f};{10:0.2f}\n".format(TIME, LAT, LON, KMH, KM_TOTAL, KM_RALLYE, KM_SECTOR, KMH_GPS, KM_TOTAL_GPS, KM_RALLYE_GPS, KM_SECTOR_GPS)
            # with open(csvFile, 'a+') as datafile:
                # datafile.write(geostring)
            SECTORTRACK_LINE.coords.addcoordinates([(LON,LAT)])
            kml.save(kmlFile)

    datastring = "data:{0:}:{1:0.1f}:{2:0.1f}:{3:0.1f}:{4:0.2f}:{5:0.2f}:{6:0.2f}:{7:0.2f}:{8:0.2f}:{9:}:{10:0.1f}:{11:}:{12:}:{13:}:{14:}:{15:}:{16:}".format(INDEX, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, DEV_AVG_KMH, GPS_CURRENT.mode, LAT, LON, int(HAS_SENSORS), int(IS_TIME_SYNC), int(IS_RECORDING))

    return datastring

def calcGPSdistance(phi1, phi2, lambda1, lambda2):
    p1 = math.radians(phi1)
    p2 = math.radians(phi2)
    l1 = math.radians(lambda1)
    l2 = math.radians(lambda2)
    x = (l2-l1) * math.cos((p1+p2)/2)
    y = (p2-p1)
    return math.sqrt(x*x + y*y) * 6371

def startTripmaster(client):
    global IS_STARTED
    IS_STARTED = True
    timed = threading.Timer(SAMPLE_TIME, pushSpeedData, [client.wsClients, "getData", "{:.1f}".format(SAMPLE_TIME)] )
    timed.start()
    timers.append(timed)
    messageToAllClients(client.wsClients, "Tripmaster gestartet!:success")
    
def stopTripmaster(client):
    global IS_STARTED
    for index, timer in enumerate(timers):
        if timer:
            timer.cancel()
    IS_STARTED = False
    messageToAllClients(client.wsClients, "Tripmaster gestoppt!:warning")
    
def pushSpeedData(clients, what, when):
    what = str(what)
    when = float(when)
    message = WebRequestHandler(what.splitlines());
    messageToAllClients(clients, message)
    timed = threading.Timer( when, pushSpeedData, [clients, what, when] )
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
    global IS_STARTED
    # Array der WebSocket Clients
    wsClients = []
    CHECKPOINTS = []

    # Client verbunden
    def check_origin(self, origin):
        return True   

    def open(self, page):
        global pi, UMIN_READER_1, UMIN_READER_2
        self.stream.set_nodelay(True)
        # Jeder WebSocket Client wird dem Array wsClients hinzugefügt
        self.wsClients.append(self)
        # Die ID
        self.id = "Client #" + str(self.wsClients.index(self) + 1) + " (" + page + ")"
        # Wenn es der erste Client ist, UMIN_READER starten
        if len(self.wsClients) == 1:
            # Verbinden mit pigpio - für VM kommentieren
            pi = pigpio.pi()
            # UMIN_READER starten - für VM kommentieren
            UMIN_READER_1 = reader(pi, GPIO_PIN_1, PULSES_PER_REV)
            UMIN_READER_2 = reader(pi, GPIO_PIN_2, PULSES_PER_REV)
            startTripmaster(self)
            logger.debug("Erster WebSocket Client verbunden")
        logger.debug("Anzahl verbundener WebSocket Clients: " + str(len(self.wsClients)))

    # the client sent a message
    def on_message(self, message):
        global IS_STARTED, IS_RECORDING, IS_NEW_TRACK, INDEX, T, T_SECTOR, KM_TOTAL, KM_RALLYE, KM_SECTOR, KM_SECTOR_PRESET, REVERSE, ACTIVE_CONFIG, COUNTDOWN, AVG_KMH_PRESET, LON_PREV, LAT_PREV
        logger.debug("Nachricht " + self.id + ": " + message + "")
        # command:param
        message = message.strip()
        messagesplit = message.split(":")
        messagesplit.append("dummyparam")
        command = messagesplit[0]
        param = messagesplit[1]
        if param == "dummy":
            param = "0"

        # Tripmaster: Start und Stop
        if command == "toggleTripmaster":
            if IS_STARTED == False:
                startTripmaster(self)
            else:
                stopTripmaster(self)
        elif command == "resetTripmaster":
            INDEX = 0
            T = 0.0
            KM_TOTAL = 0.0
            KM_RALLYE = 0.0
            KM_SECTOR = 0.0
            KM_SECTOR_PRESET = 0.0
            IS_NEW_TRACK = True
            REVERSE = 1
            messageToAllClients(self.wsClients, "Tripmaster zurückgesetzt!:success")

        # Aufzeichnung
        elif command == "toggleRecording":
            if IS_RECORDING == False:
                IS_RECORDING = True
                messageToAllClients(self.wsClients, "Aufzeichung gestartet!:success")
            else:
                IS_RECORDING = False
                messageToAllClients(self.wsClients, "Aufzeichung gestoppt!:warning")
                
        # Sektoren
        elif command == "resetSector":
            if IS_STARTED == True:
                T_SECTOR = 0.0
                KM_SECTOR = 0.0
                KM_SECTOR_PRESET = 0.0
                IS_NEW_TRACK = True
                messageToAllClients(self.wsClients, "Sektorzähler zurückgesetzt!:success:sectorReset")
            else:
                messageToAllClients(self.wsClients, "Tripmaster noch nicht gestartet!:warning")
        elif command == "setSectorLength":
            KM_SECTOR_PRESET = float(param)
            messageToAllClients(self.wsClients, "Sektor auf "+locale.format("%.2f", KM_SECTOR_PRESET)+" km gesetzt!:success:sectorLengthset")
        elif command == "toggleReverse":
            REVERSE = REVERSE * -1
            if REVERSE == -1:
                messageToAllClients(self.wsClients, "Verfahren! km-Zähler rückwärts:warning")
            else:
                messageToAllClients(self.wsClients, "km-Zähler wieder normal:success")

        # Orientierungskontrollen
        elif command == "registerPoint":
            # Aktuelle Position
            GPS_CURRENT = gpsd.get_current()
           # Ein 3D Fix ist notwendig, sonst zu ungenau
            if GPS_CURRENT.mode >= 2:
                if param == "roundabout":
                    ROUNDABOUTS.newpoint(coords=[(GPS_CURRENT.lon,GPS_CURRENT.lat)]) # Jeder Punkt als Teil _einer_ MultiGeometry (z.B. Kreisverkehre zählen)
                    messageToAllClients(self.wsClients, "Kreisverkehr registriert:success")
                elif param == "checkpoint":
                    # Anfrage zurückschicken, welche(r) Buchstabe(n)/Zahl(en)
                    CHECKPOINT = kml.newmultigeometry()
                    self.CHECKPOINTS.append(CHECKPOINT)
                    logger.debug(str(self.CHECKPOINTS.index(CHECKPOINT)));
                    # CHECKPOINTS = kml.newmultigeometry(name=("OK"+str(INDEX))) # Jeder Punkt als Teil _einer eigenen_ MultiGeometry (z.B. OK mit Buchstaben/Zahl)
                    # CHECKPOINTS.style.iconstyle.icon.href = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Zeichen_310-50_-_Ortstafel_%28Vorderseite%29_mit_Kreis%2C_StVO_1992.svg/200px-Zeichen_310-50_-_Ortstafel_%28Vorderseite%29_mit_Kreis%2C_StVO_1992.svg.png"
                    # CHECKPOINTS.newpoint(coords=[(GPS_CURRENT.lon,GPS_CURRENT.lat)])
                elif param == "tmp":
                    logger.debug(str(len(self.CHECKPOINTS)))
                    logger.debug(str(self.CHECKPOINTS[0]))
                    self.CHECKPOINTS[0].name = "nachgetragen"
            else:
                messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")



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

        # Konfiguration
        elif command == "changeConfig":
            ACTIVE_CONFIG = param
            config.set("Settings", "aktiv", ACTIVE_CONFIG)
            with open(configFileName, "w") as configfile:    # save
                config.write(configfile)
            setConfig()
            self.write_message("Neue Konfiguration - '"+ ACTIVE_CONFIG +"':success")
        elif command == "getConfig":
            self.write_message("getConfig:"+getConfig())
        elif command == "writeConfig":
            paramsplit = param.split("&")
            for keyvalues in paramsplit:
                keyvalue = keyvalues.split("=")
                config.set(ACTIVE_CONFIG, keyvalue[0], keyvalue[1])
            with open(configFileName, "w") as configfile:    # save
                config.write(configfile)
            setConfig()
            self.write_message("Konfiguration '" + ACTIVE_CONFIG + "' gespeichert:success")

        # Raspi Steuerung
        elif command == "sudoReboot":
            messageToAllClients(self.wsClients, "Starte Raspi neu...")
            subprocess.call("sudo reboot", shell=True)
        elif command == "sudoHalt":
            messageToAllClients(self.wsClients, "Fahre Raspi herunter...")
            subprocess.call("sudo shutdown -h now", shell=True)
        else:
            self.write_message("Unbekannter Befehl: " + command)
        
    # Client getrennt
    def on_close(self):
        # Aus der Liste laufender Clients entfernen
        self.wsClients.remove(self)
    
        if len(self.wsClients) == 0:
            # UMIN_READER stoppen - für VM kommentieren
            UMIN_READER_1.cancel()
            UMIN_READER_2.cancel()
            # Verbindung mit pigpio beenden - für VM kommentieren
            pi.stop()
            
            # Tripmaster stoppen
            stopTripmaster(self)
            logger.debug("Letzter WebSocket Client getrennt")
        
        logger.debug("Anzahl verbundener Clients: " + str(len(self.wsClients)))

#-------------------------------------------------------------------

class Web_Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/dashboard.html", DashboardHandler),
            (r"/settings.html", SettingsHandler),
            (r"/static/(.*)", StaticHandler),
            (r"/(favicon.ico)", StaticHandler),
          ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug = DEBUG,
            autoescape = None
        )
        tornado.web.Application.__init__(self, handlers, **settings)

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
    options.logging = None
    ws_app = tornado.web.Application([(r"/(.*)", WebSocketHandler),])
    ws_server = tornado.httpserver.HTTPServer(ws_app, ssl_options={
        "certfile": tripmasterPath+"/certs/servercert.pem",
        "keyfile": tripmasterPath+"/certs/serverkey.pem",
    })
    ws_server.listen(websocketPort)

    web_server = tornado.httpserver.HTTPServer(Web_Application(), ssl_options={
        "certfile": tripmasterPath+"/certs/servercert.pem",
        "keyfile": tripmasterPath+"/certs/serverkey.pem",
    })
    web_server.listen(443)
    tornado.ioloop.IOLoop.instance().start()
except (KeyboardInterrupt, SystemExit):
    for index, timer in enumerate(timers):
        if timer:
            timer.cancel()
    logger.debug("Tornado beendet")