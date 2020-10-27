#!/usr/bin/env python3

from __future__ import print_function
from datetime import datetime
from logging.handlers import RotatingFileHandler
from read_RPM import reader
from tornado.options import options
import configparser
import glob
import gpsd
import io
import locale
import logging
import math
import os.path
import pickle
import pigpio
import pytz
import RPi.GPIO as GPIO
import simplekml
import subprocess
import sys
import threading
import time
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop

#-------------------------------------------------------------------

websocketPort = 7070

DEBUG = False
# Kommandozeilenargument
if len(sys.argv) > 1:
    DEBUG = (sys.argv[1] == "debug")

### --- Konfiguration Tripmaster ---
# Komma als Dezimaltrennzeichen
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
# Zeitzonen
tz_utc = pytz.timezone('UTC')
tz_berlin = pytz.timezone('Europe/Berlin')
# Programmpfad für Dateiausgaben
tripmasterPath = os.path.dirname(os.path.abspath(__file__))

### Konfiguration Logger
logging.basicConfig(filename = tripmasterPath+"/out/tripmaster.log", format="%(asctime)s.%(msecs)03d - line %(lineno)d - %(levelname)s - %(message)s", datefmt="%d.%m.%Y %H:%M:%S", level=logging.WARNING)
logger = logging.getLogger('Tripmaster')
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.info("Tornado gestartet")
logger.info("DEBUG: " + str(DEBUG))

### Konfiguration Antriebswellensensor(en)
# Einrichten der BCM GPIO Nummerierung
GPIO.setmode(GPIO.BCM)
# GPIO Pins der Sensoren
GPIO_PIN_1 = 17 # weiß
GPIO_PIN_2 = 18 # blau
# Setup als input
GPIO.setup(GPIO_PIN_1, GPIO.IN)
GPIO.setup(GPIO_PIN_2, GPIO.IN)
# Verbindung zu pigpio Deamon
pi = None
# Die UMIN_READER
UMIN_READER_1 = None
UMIN_READER_2 = None
# Impulse pro Umdrehung
PULSES_PER_REV = 1.0

### GPS Deamon
gpsd.connect()

### Konfiguration Fahrzeug
# INI-Datei
config = configparser.RawConfigParser()
# erhält Groß-/Kleinschreibung
config.optionxform = str
configFileName = tripmasterPath+"/tripmaster.ini"
config.read(configFileName)
# aktive Konfiguration
ACTIVE_CONFIG = config.get("Settings", "aktiv")

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

# Fortlaufender Index
INDEX = 0
# Messen alle ... Sekunden
SAMPLE_TIME = 1.0
# Zeit ist synchronisiert?
IS_TIME_SYNC = None
# Hat Antriebswellensensor?
HAS_SENSORS = False
# Durchschnittsgeschwindigkeit - aktuell und Vorgabe
AVG_KMH = 0.0
AVG_KMH_PRESET = 0.0
# Rückwärtszählen beim Verfahren
REVERSE = 1
# Zeitvorgabe der GLP
COUNTDOWN = 0

# Geodatenausgabe als KML und/oder CSV
KML = None
POINTS = None

# Folders
FOLDER_STAGE = None
FOLDER_SECTORTRACKS = None
FOLDER_COUNTPOINTS = None
FOLDER_CHECKPOINTS = None

FOLDERS = {
    "stage": FOLDER_STAGE,
    "sectortrack": FOLDER_SECTORTRACKS,
    "countpoint": FOLDER_COUNTPOINTS,
    "checkpoint": FOLDER_CHECKPOINTS,
    }

# Styles
TRACK_RED = simplekml.Style()
TRACK_RED.linestyle.width = 5
TRACK_RED.linestyle.color = "ff4f53d9"

TRACK_GREEN = simplekml.Style()
TRACK_GREEN.linestyle.width = 5
TRACK_GREEN.linestyle.color = "ff5cb85c"

class POINT:
    global KML
    def __init__(self, name, icon, iconcolor, mapicon = ""):
        self.name = name
        self.icon = icon
        self.iconcolor = "var(--tm-" + iconcolor + ")"
        self.mapicon = mapicon
        enabledIcon = tripmasterPath + "/static/kmz/" + self.mapicon + ".gif"
        disabledIcon = tripmasterPath + "/static/kmz/" + self.mapicon + "_disabled.gif"
        if os.path.exists(enabledIcon):
            self.style = simplekml.Style()
            self.style.iconstyle.icon.href = KML.addfile(enabledIcon)
        if os.path.exists(disabledIcon):
            self.disabledstyle = simplekml.Style()
            self.disabledstyle.iconstyle.icon.href = KML.addfile(disabledIcon)

def getStyleByName(name, visibility):
    for P in POINTS:
        if POINTS[P].name == name:
            if visibility == 1:
                return POINTS[P].style
            else:
                return POINTS[P].disabledstyle

CHECKPOINTS = []
COUNTPOINTS = []

# Rallye, Etappe und Abschnitt sind SECTIONs
class SECTION:
    #                  Nummer  Messpunkt Startzeit  Endzeit     Streckenvorgabe  Strecke   Strecke (GPS) Track         Länge      Breite
    def __init__(self, no = 0, t = 0.0,  start = 0, finish = 0, preset = 0.0,    km = 0.0, km_gps = 0.0, track = None, lon = 0.0, lat = 0.0):
        self.no = no
        self.t = t
        self.start = start
        self.finish = finish
        self.init = False
        self.preset = preset
        self.km = km
        self.km_gps = km_gps
        self.track = track
        self.lon = lon
        self.lat = lat
        self.lon_prev = None
        self.lat_prev = None
        self.subsection = None
    
    def getDuration(self):
        if (self.start > 0) and (self.finish > 0):
            return max(self.finish - self.start, 0)
        else:
            return 0
            
    def isStarted(self):
        isStarted = (self.start > 0) and (self.start < datetime.timestamp(datetime.now()))
        return isStarted
        
RALLYE = None
STAGE = None
SECTOR = None

# Rallye initialisieren
def initRallye():
    global KML, KML_FILE, RALLYE, STAGE, SECTOR, POINTS, INDEX
    KML = simplekml.Kml(open=1)
    KML_FILE = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.kmz".format(datetime.now());
    POINTS = {
        # Etappenstart und -ziel
        "stage_start": POINT("Start Etappe", "fas fa-flag-checkered", "red", "checkered_flag_start"),
        "stage_finish": POINT("Ende Etappe", "fas fa-flag-checkered", "green", "checkered_flag_finish"),

        # Punkte
        "null": POINT("Keine", "fas fa-question", "red"),
        # Zählpunkte
        "countpoint": POINT("Sonstiges", "fas fa-hashtag", "blue", "countpoint"),
        # Orientierungskontrollen
        "roundabout": POINT("Kreisverkehr", "fas fa-sync", "blue", "roundabout"),
        "townsign": POINT("Ortsschild", "fas fa-sign", "yellow", "townsign"),
        "stampcheck": POINT("Stempelkontrolle", "fas fa-stamp", "red", "stampcheck"),
        "mutecheck": POINT("Stummer Wächter", "fas fa-neuter", "green", "mutecheck"),
        "checkpoint": POINT("Sonstige OK", "fas fa-map-marker-alt", "green", "checkpoint"),
        }
    KML.savekmz(KML_FILE)
    INDEX = 0
    RALLYE = SECTION() # unpickleData("rallye")
    RALLYE.subsection = SECTION()
    STAGE = RALLYE.subsection
    STAGE.subsection = SECTION()
    SECTOR = STAGE.subsection
    logger.debug("initRallye")

# Etappe initialisieren
def initStage(LON, LAT):
    global FOLDERS, STAGE, SECTOR
    STAGE.no += 1
    FOLDERS["stage"] = KML.newfolder(name="Etappe " + str(STAGE.no))
    FOLDERS["sectortrack"] = FOLDERS["stage"].newfolder(name="Abschnitte")
    FOLDERS["countpoint"] = FOLDERS["stage"].newfolder(name="Zählpunkte")
    FOLDERS["checkpoint"] = FOLDERS["stage"].newfolder(name="Orientierungskontrollen")
    STAGE.init = True
    STAGE.km = 0.0
    SECTOR.no = 0
    setPoint(FOLDERS["stage"], POINTS["stage_start"].style, LON, LAT, "", POINTS["stage_start"].name)    
    logger.debug("initStage")
    initSector(LON, LAT)

# Abschnitt initialisieren
def initSector(LON, LAT):
    global KML_FILE, SECTOR, REVERSE
    if SECTOR.no > 1:
        # Alten Abschnitt mit den aktuellen Koordinaten abschließen
        SECTOR.track.coords.addcoordinates([(LON,LAT)])
        KML.savekmz(KML_FILE)
    SECTOR.no += 1
    # Neuen Abschnitt beginnen
    SECTOR.track = FOLDERS["sectortrack"].newlinestring(name="Abschnitt "+str(SECTOR.no))
    if (SECTOR.no % 2 == 0):
        SECTOR.track.style = TRACK_RED
    else:
        SECTOR.track.style = TRACK_GREEN
    SECTOR.track.coords.addcoordinates([(LON,LAT)])
    KML.savekmz(KML_FILE)
    # Abschnitt zurücksetzen
    SECTOR.t = 0.0
    SECTOR.km = 0.0
    SECTOR.preset = 0.0
    REVERSE = 1
    logger.debug("initSector")

def setPoint(POINTFOLDER, POINTSTYLE, LON, LAT, DESCRIPTION, NAME=""):
    global KML_FILE
    NEWPOINT = POINTFOLDER.newpoint(coords=[(LON,LAT)], description = DESCRIPTION, name = NAME, visibility = 1)
    NEWPOINT.style = POINTSTYLE
    KML.savekmz(KML_FILE)
    logger.debug("setPoint")
    return NEWPOINT

# csvFile = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.csv".format(datetime.now());

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
    if (len(GPS_CURRENT.time) == 24):
        naive = datetime.strptime(GPS_CURRENT.time, '%Y-%m-%dT%H:%M:%S.%fZ')
        utc = tz_utc.localize(naive)
        local = utc.astimezone(tz_berlin)
        subprocess.call("sudo date -u -s '"+str(local)+"' > /dev/null 2>&1", shell=True)
        return True
    else:
        return False

def getData():
    global RALLYE, SECTOR, STAGE, IS_TIME_SYNC, HAS_SENSORS, N_SENSORS, INDEX, REVERSE, AVG_KMH, AVG_KMH_PRESET
    
    # Ein 0 V Potential an einem der GPIO Pins aktiviert die Antriebswellensensoren
    if ((GPIO.input(GPIO_PIN_1) == 0) or (GPIO.input(GPIO_PIN_2) == 0)) and not HAS_SENSORS:
        HAS_SENSORS = True
        logger.info("Antriebswellensensor(en) automatisch aktiviert!")

    # Index hochzählen
    INDEX += 1
    # Geschwindigkeit in Kilometer pro Stunde
    KMH     = 0.0
    KMH_GPS = 0.0
    
    # Lokale Variable von STAGE.isStarted()
    STAGE_isStarted = STAGE.isStarted()

    ### GPS

    # Aktuelle Position
    GPS_CURRENT = gpsd.get_current()
    if DEBUG:
        GPS_CURRENT.mode = 3
        GPS_CURRENT.lon = 8.0 + INDEX/5000
        GPS_CURRENT.lat = 50.0 + INDEX/5000
        GPS_CURRENT.hspeed = 20
        IS_TIME_SYNC = True

    # Alle 10 Durchläufe Zeit synchronisieren
    if (INDEX % 10 == 0) or (IS_TIME_SYNC == None):
        IS_TIME_SYNC = syncTime(GPS_CURRENT)

    # Aktuelle Zeit
    TIME = datetime.now()

    # Gefahrene Distanz in km (berechnet aus Geokoordinaten)
    DIST = 0.0

    # Mindestens ein 2D Fix
    if (GPS_CURRENT.mode >= 2):

        # KMH_GPS = GPS_CURRENT.speed() * 3.6 - gibt auf einmal nur noch 0.0 zurück
        if (GPS_CURRENT.hspeed > 1.0) and STAGE_isStarted:
            KMH = GPS_CURRENT.hspeed * 3.6

        KMH_GPS = KMH
            
        STAGE.lon = GPS_CURRENT.lon
        STAGE.lat = GPS_CURRENT.lat

        if (STAGE.lon_prev is not None) and (STAGE.lat_prev is not None) and (KMH_GPS > 0.0) and STAGE_isStarted:
            DIST = calcGPSdistance(STAGE.lon_prev, STAGE.lon, STAGE.lat_prev, STAGE.lat)

        RALLYE.km     += DIST
        RALLYE.km_gps  = RALLYE.km
        STAGE.lon_prev = STAGE.lon
        STAGE.lat_prev = STAGE.lat
        STAGE.km      += DIST * REVERSE
        STAGE.km_gps   = STAGE.km
        SECTOR.km     += DIST * REVERSE
        SECTOR.km_gps  = SECTOR.km

    ### Antriebswellensensor(en)

    # Umdrehungen der Antriebswelle(n) pro Minute
    UMIN = 0.0

    if HAS_SENSORS:

        # UMIN ermitteln
        UMIN = int(UMIN_READER_1.RPM() + 0.5)
        if N_SENSORS > 1:
            UMIN += int(UMIN_READER_2.RPM() + 0.5)
            UMIN  = UMIN / 2
        # Geschwindigkeit in Meter pro Sekunde
        if STAGE_isStarted:
            MS = UMIN / TRANSMISSION_RATIO / 60 * TYRE_SIZE

        # Geschwindigkeit in Kilometer pro Stunde
        KMH = MS * 3.6
        # Zurückgelegte Kilometer - Rallye, Etappe und Abschnitt (Rückwärtszählen beim Umdrehen außer bei Rallye)
        RALLYE.km += MS * SAMPLE_TIME / 1000
        STAGE.km  += MS * SAMPLE_TIME / 1000 * REVERSE
        SECTOR.km += MS * SAMPLE_TIME / 1000 * REVERSE

    if STAGE_isStarted:
        # Messzeitpunkte Abschnitt
        SECTOR.t += SAMPLE_TIME

    # % zurückgelegte Strecke im Abschnitt
    FRAC_SECTOR_DRIVEN = 0
    if SECTOR.preset > 0:
        FRAC_SECTOR_DRIVEN = int(min(SECTOR.km / SECTOR.preset * 100, 100))
    # noch zurückzulegende Strecke im Abschnitt (mit der 0.005 wird der Wert 0 in der TextCloud vermieden)
    SECTOR_PRESET_REST = max(SECTOR.preset - SECTOR.km, 0) #0.005)

    # Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
    DEV_AVG_KMH = 0.0

    if SECTOR.t > 0.0:
        # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde im Abschnitt
        AVG_KMH = SECTOR.km * 1000 / SECTOR.t * 3.6
        if AVG_KMH_PRESET > 0.0:
            DEV_AVG_KMH = AVG_KMH - AVG_KMH_PRESET

    STAGE_TIMETOSTART = 0
    STAGE_TIMETOFINISH = 0
    STAGE_FRACTIME = 0.0
    if STAGE_isStarted:
        # Etappe initialisieren, wenn noch nicht geschehen
        if STAGE.init == False:
            initStage(STAGE.lon, STAGE.lat)                    
         
        # Alle 5 Durchläufe Geodaten abspeichern
        # Bounding Box von Deutschland: (5.98865807458, 47.3024876979, 15.0169958839, 54.983104153)),
        if (INDEX % 5 == 0) and IS_TIME_SYNC and 15.1 > STAGE.lon > 5.9 and 55.0 > STAGE.lat > 47.3:
            # geostring = "{0:%d.%m.%Y %H:%M:%S};{1:};{2:};{3:0.1f};{4:0.2f};{5:0.2f};{6:0.2f};{7:0.1f};{8:0.2f};{9:0.2f};{10:0.2f}\n".format(TIME, STAGE.lon, STAGE.lat, KMH, RALLYE.km, STAGE.km, SECTOR.km, KMH_GPS, RALLYE.km_gps, STAGE.km_gps, SECTOR.km_gps)
            # with open(csvFile, 'a+') as datafile:
                # datafile.write(geostring)
            SECTOR.track.coords.addcoordinates([(STAGE.lon,STAGE.lat)])
            pickleData(RALLYE, "rallye")
            KML.savekmz(KML_FILE)

        if STAGE.getDuration() > 0:
            STAGE_TIMETOFINISH = int(STAGE.finish - datetime.timestamp(datetime.now())) # int(time.time())
            STAGE_FRACTIME = round((1 - STAGE_TIMETOFINISH / STAGE.getDuration()) * 100)
    else:
        if STAGE.start > 0:
            STAGE_TIMETOSTART = int(datetime.timestamp(datetime.now()) - STAGE.start)

    datastring = "data:{0:}:{1:0.1f}:{2:0.1f}:{3:0.1f}:{4:0.2f}:{5:0.2f}:{6:0.2f}:{7:0.2f}:{8:0.2f}:{9:}:{10:0.1f}:{11:}:{12:0.6f}:{13:0.6f}:{14:}:{15:}:{16:}:{17:}:{18:}:{19:}".format(INDEX, UMIN, KMH, AVG_KMH, RALLYE.km, STAGE.km, SECTOR.km, SECTOR.preset, SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, DEV_AVG_KMH, GPS_CURRENT.mode, STAGE.lon, STAGE.lat, int(HAS_SENSORS), int(IS_TIME_SYNC), int(STAGE_isStarted), int(STAGE_FRACTIME), STAGE_TIMETOSTART, STAGE_TIMETOFINISH)

    return datastring

def calcGPSdistance(lambda1, lambda2, phi1, phi2):
    l1 = math.radians(lambda1)
    l2 = math.radians(lambda2)
    p1 = math.radians(phi1)
    p2 = math.radians(phi2)
    x  = (l2-l1) * math.cos((p1+p2)/2)
    y  = (p2-p1)
    return math.sqrt(x*x + y*y) * 6371

def startTripmaster(client):
    timed = threading.Timer(SAMPLE_TIME, pushSpeedData, [client.wsClients, "getData", "{:.1f}".format(SAMPLE_TIME)] )
    timed.start()
    timers.append(timed)
    messageToAllClients(client.wsClients, "Tripmaster gestartet!:success")

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

def pickleData(data, filename):
    with open(tripmasterPath + '/out/' + filename, 'wb') as fp:
        pickle.dump(data, fp)
   
def unpickleData(filename):
    with open(tripmasterPath + '/out/' + filename, 'rb') as fp:
        return pickle.load(fp)
    
### WebSocket server tornado <-> WebInterface
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    # Array der WebSocket Clients
    wsClients = []

    # Client verbunden
    def check_origin(self, origin):
        return True

    def open(self, page):
        global pi, UMIN_READER_1, UMIN_READER_2, CHECKPOINTS, COUNTPOINTS
        self.stream.set_nodelay(True)
        # Jeder WebSocket Client wird dem Array wsClients hinzugefügt
        self.wsClients.append(self)
        # Die ID
        self.id = "Client #" + str(self.wsClients.index(self) + 1) + " (" + page + ")"
        # Wenn es der erste Client ist, alles initialisieren
        if len(self.wsClients) == 1:
            # Verbinden mit pigpio
            pi = pigpio.pi()
            # UMIN_READER starten
            UMIN_READER_1 = reader(pi, GPIO_PIN_1, PULSES_PER_REV)
            UMIN_READER_2 = reader(pi, GPIO_PIN_2, PULSES_PER_REV)
            # Alle Parameter auf null
            initRallye()
            # Timer starten
            timed = threading.Timer(SAMPLE_TIME, pushSpeedData, [self.wsClients, "getData", "{:.1f}".format(SAMPLE_TIME)] )
            timed.start()
            timers.append(timed)
            
            messageToAllClients(self.wsClients, "Tripmaster gestartet!:success")
            logger.info("Erster WebSocket Client verbunden")

        CHECKPOINTS = unpickleData('checkpoint')
        COUNTPOINTS = unpickleData("countpoint")

        # Die Buttondefinition aus der INI-Datei lesen
        for b in range(4):
            button = "button-" + str(b+1)
            config.read(configFileName)
            buttonconfig = config.get("Settings", button)
            buttonconfigsplit = buttonconfig.split(":")
            pointCategory = buttonconfigsplit[0]
            pointType = buttonconfigsplit[1]
            self.write_message("::setButtons#" + button + "#" + POINTS[pointType].icon + "#" + POINTS[pointType].iconcolor + "#" + pointCategory + "#" + pointType)

        stagestatus = "stage_start"
        if STAGE.start == 0:
            stagestatus = "stage_finish"

        messageToAllClients(self.wsClients, "::setButtons#button-togglestage#" + POINTS[stagestatus].icon + "#" + POINTS[stagestatus].iconcolor + "#toggleStage#")

        logger.info("OPEN - Anzahl verbundener Clients: " + str(len(self.wsClients)))

    # the client sent a message
    def on_message(self, message):
        global ACTIVE_CONFIG, KML, FOLDERS, STAGE, REVERSE, COUNTDOWN, AVG_KMH_PRESET
        global INDEX # für DEBUG
        logger.debug("Nachricht " + self.id + ": " + message + "")
        # command:param
        message = message.strip()
        messagesplit = message.split(":")
        messagesplit.append("dummyparam")
        command = messagesplit[0]
        param = messagesplit[1]
        if param == "dummy":
            param = "0"

    # Strecke
        # Abschnitt
        if command == "resetSector":
            currentPos = self.getGPS();
            if currentPos is not None:
                initSector(currentPos.lon, currentPos.lat)
                messageToAllClients(self.wsClients, "Abschnittszähler zurückgesetzt!:success:sectorReset")

        # Abschnittsvorgabe setzen
        elif command == "setSectorLength":
            SECTOR.preset = float(param) 
            if float(param) > 0.0:
                messageToAllClients(self.wsClients, "Abschnitt auf "+locale.format("%.2f", SECTOR.preset)+" km gesetzt!:success:sectorLengthset")
            else:
                messageToAllClients(self.wsClients, "Vorgabe zurückgesetzt:success")
        
        # Verfahren
        elif command == "toggleReverse":
            REVERSE = REVERSE * -1
            if REVERSE == -1:
                messageToAllClients(self.wsClients, "Verfahren! km-Zähler rückwärts:warning")
            else:
                messageToAllClients(self.wsClients, "km-Zähler wieder normal:success")

        # Etappe starten/stoppen
        elif command == "toggleStage":
            currentPos = self.getGPS();
            if currentPos is not None:
                if (STAGE.start == 0):
                    STAGE.start = datetime.timestamp(datetime.now()) # int(time.time())
                    initStage(currentPos.lon, currentPos.lat)                    
                    messageToAllClients(self.wsClients, "Etappe gestartet:success:setButtons#button-togglestage#" + POINTS["stage_start"].icon + "#" + POINTS["stage_start"].iconcolor + "#toggleStage#")
                else:
                    STAGE.start = 0
                    STAGE.init = False
                    setPoint(FOLDERS["stage"], POINTS["stage_finish"].style, currentPos.lon, currentPos.lat, "", POINTS["stage_finish"].name)
                    messageToAllClients(self.wsClients, "Etappe beendet:success:setButtons#button-togglestage#" + POINTS["stage_finish"].icon + "#" + POINTS["stage_finish"].iconcolor + "#toggleStage#")                    
        
        # Zeit bis zum Ziel der Etappe
        elif command == "setStageFinish":
            if param == 'null':
                STAGE.finish = 0
                messageToAllClients(self.wsClients, "Etappenzielzeit gelöscht:success")
            else:
                STAGE.finish = int(int(param) / 1000)
                messageToAllClients(self.wsClients, "Etappenzielzeit gesetzt:success")
        
        # Zeit bis zum Start der Etappe
        elif command == "setStageStart":
            if param == 'null':
                STAGE.start = 0
                messageToAllClients(self.wsClients, "Etappenstartzeit gelöscht:success:setButtons#button-togglestage#" + POINTS["stage_finish"].icon + "#" + POINTS["stage_finish"].iconcolor + "#toggleStage#")
            else:
                STAGE.start = int(int(param) / 1000)
                starttime = datetime.fromtimestamp(STAGE.start).strftime("%H&#058;%M")
                messageToAllClients(self.wsClients, "Etappe startet automatisch um " + starttime + " Uhr:success:setButtons#button-togglestage#" + POINTS["stage_start"].icon + "#" + POINTS["stage_start"].iconcolor + "#toggleStage#")

    # Gleichmäßigkeitsprüfung
        elif command == "startRegtest":
            COUNTDOWN = int(param)
            startRegtest(self)
            messageToAllClients(self.wsClients, "GLP gestartet:success:regTestStarted")
        elif command == "setRegtestLength":
            SECTOR.preset = float(param)
        elif command == "setAvgSpeed":
            AVG_KMH_PRESET = float(param)
            messageToAllClients(self.wsClients, "avgspeed:" + param)
        elif command == "stopRegtest":
            COUNTDOWN = 0
            AVG_KMH_PRESET = 0.0
            messageToAllClients(self.wsClients, "countdown:0")
            messageToAllClients(self.wsClients, "GLP gestoppt:success:regTestStopped")

    # Settings
        # Raspi Steuerung
        elif command == "sudoReboot":
            messageToAllClients(self.wsClients, "Starte Raspi neu...")
            subprocess.call("sudo reboot", shell=True)
        elif command == "sudoHalt":
            messageToAllClients(self.wsClients, "Fahre Raspi herunter...")
            subprocess.call("sudo shutdown -h now", shell=True)
        
        # Tripmaster / Rallye
        elif command == "resetRallye":
            CHECKPOINTS.clear()
            COUNTPOINTS.clear()
            pickleData(CHECKPOINTS, "checkpoint")
            pickleData(CHECKPOINTS, "countpoint")
            KML = simplekml.Kml(open=1)
            initRallye()
            
        # KMZ Dateien herunterladen oder löschen
        elif command == "getFiles":
            filelist = glob.glob(tripmasterPath + "/out/*.kmz")
            filelist.sort(reverse = True)
            for file in filelist:
                messageToAllClients(self.wsClients, "::downloadfiles#" + os.path.basename(file))
        elif command == "deleteFile":
            try:
                os.remove(tripmasterPath + "/out/" + param)
                self.write_message("Datei " + param + " gelöscht:success")
            except:
                self.write_message("Fehler beim Löschen von " + param + ":error")

        # Sensorkonfiguration
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

        # Buttons definieren
        elif (command.startswith("button")):
            button = command
            buttonNo = button.replace("button-", "")
            pointCategory = param
            pointType = messagesplit[2]
            # In ini abspeichern
            config.set("Settings", button, pointCategory+":"+pointType)
            with open(configFileName, "w") as configfile:
                config.write(configfile)
            messageToAllClients(self.wsClients, "Button " + buttonNo + " als '" + POINTS[pointType].name + "' definiert:success:setButtons#" + button + "#" + POINTS[pointType].icon + "#" + POINTS[pointType].iconcolor + "#" + pointCategory + "#" + pointType)
        
        # Punkte registrieren
        elif (command == "countpoint") or (command == "checkpoint"):
            currentPos = self.getGPS();
            if currentPos is not None:
                NEWPOINT = setPoint(FOLDERS[command], POINTS[param].style, currentPos.lon, currentPos.lat, POINTS[param].name)
                if command == "countpoint":
                    COUNTPOINTS.append(NEWPOINT)
                    id = COUNTPOINTS.index(NEWPOINT)
                    pickleData(COUNTPOINTS, command)
                    # // IDEE - Raussuchen der Punktgeometrie nach der ID des KML-Objektes und dann ändern, würde die Listen CHECKPOINTS / COUNTPOINTS obsolet machen
                    # logger.debug("NEWPOINT.id: " + NEWPOINT.id)
                elif command == "checkpoint":
                    CHECKPOINTS.append(NEWPOINT)
                    id = CHECKPOINTS.index(NEWPOINT)
                    pickleData(CHECKPOINTS, command)

                messageToAllClients(self.wsClients, POINTS[param].name + " registriert:success:" + command + "Registered#" + str(id) + "#" + POINTS[param].name + "##1")

        # Punkte ändern
        elif command == "changepoint":
            paramsplit = param.split("&")
            pointtype = paramsplit[0]
            id = int(paramsplit[1])
            description = paramsplit[2]
            name = paramsplit[3]
            visibility = int(paramsplit[4])
            # Parameter des Punktes ändern
            if pointtype == "countpoint":
                COUNTPOINTS[id].visibility = visibility
                COUNTPOINTS[id].style = getStyleByName(description, visibility)
                pickleData(COUNTPOINTS, pointtype)
            elif pointtype == "checkpoint":
                CHECKPOINTS[id].visibility = visibility
                CHECKPOINTS[id].style = getStyleByName(description, visibility)
                CHECKPOINTS[id].name = name
                CHECKPOINTS[id].description = description
                pickleData(CHECKPOINTS, pointtype)

            KML.savekmz(KML_FILE)
            self.write_message("ID " + str(id) + " - " + description + " geändert:success")

        # Alle Punkte beim Start laden
        elif command == "getAllPoints":
            for COUNTPOINT in COUNTPOINTS:
                id = COUNTPOINTS.index(COUNTPOINT)
                description = COUNTPOINT.description
                name = COUNTPOINT.name
                visibility = COUNTPOINT.visibility
                self.write_message("::countpointRegistered#" + str(id) + "#" + description + "#" + name + "#" + str(visibility))
            for CHECKPOINT in CHECKPOINTS:
                id = CHECKPOINTS.index(CHECKPOINT)
                description = CHECKPOINT.description
                name = CHECKPOINT.name
                visibility = CHECKPOINT.visibility
                self.write_message("::checkpointRegistered#" + str(id) + "#" + description + "#" + name + "#" + str(visibility))

        else:
            self.write_message("Unbekannter Befehl - " + command + ":error")

    def getGPS(self):
        # Aktuelle Position
        GPS_CURRENT = gpsd.get_current()
        # Mindestens ein 2D Fix
        if GPS_CURRENT.mode >= 2:
            return GPS_CURRENT
        else:
            if DEBUG:
                GPS_CURRENT.lon = 8.0 + INDEX/5000
                GPS_CURRENT.lat = 50.0 + INDEX/5000
                return GPS_CURRENT
            messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")
            return None

    # Client getrennt
    def on_close(self):
        global STAGE, FOLDERS
        # Aus der Liste laufender Clients entfernen
        self.wsClients.remove(self)

        if len(self.wsClients) == 0:
            # UMIN_READER stoppen
            UMIN_READER_1.cancel()
            UMIN_READER_2.cancel()
            # Verbindung mit pigpio beenden
            pi.stop()

            # Tripmaster stoppen
            for index, timer in enumerate(timers):
                if timer:
                    timer.cancel()
            # Laufende Etappe beenden
            if (STAGE is not None) and STAGE.isStarted():
                STAGE.start = 0
                currentPos = self.getGPS();
                if currentPos is not None:
                    setPoint(FOLDERS["stage"], POINTS["stage_finish"].style, currentPos.lon, currentPos.lat, "", POINTS["stage_finish"].name)
                    
            logger.info("Letzter WebSocket Client getrennt")

        logger.info("CLOSE - Anzahl noch verbundener Clients: " + str(len(self.wsClients)))

#-------------------------------------------------------------------

class Web_Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/dashboard.html", DashboardHandler),
            (r"/settings.html", SettingsHandler),
            (r"/static/(.*)", StaticHandler),
            (r"/(favicon.ico)", StaticHandler),
            (r"/out/(.*)", DownloadHandler),
          ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug = int(DEBUG),
            autoescape = None
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class DashboardHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        self.render(
            "dashboard.html",
            debug = int(DEBUG),
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
            debug = int(DEBUG),
            sample_time = int(SAMPLE_TIME * 1000),
            sector_reverse = sector_reverse,
            active_config = ACTIVE_CONFIG,
        )

# deliver static files to page
class StaticHandler(tornado.web.RequestHandler):
    def get(self, filename):
        with open(filename, "r") as fh:
            self.file = fh.read()
        # write to page
        if filename.endswith(".css"):
            self.set_header("Content-Type", "text/css")
        elif filename.endswith(".js"):
            self.set_header("Content-Type", "text/javascript")
        elif filename.endswith(".png"):
            self.set_header("Content-Type", "image/png")
        elif filename.endswith(".json"):
            self.set_header("Content-Type", "application/json")
        self.write(self.file)

class DownloadHandler(tornado.web.RequestHandler):
    def get(self, filename):
        with open(tripmasterPath+"/out/"+filename, "rb") as fh:
            self.file = fh.read()
        if filename.endswith(".kmz"):
            self.set_header("Content-Type", "application/vnd.google-earth.kmz")
        if filename.endswith(".log"):
            self.set_header("Content-Type", "text/txt")
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
    logger.info("Tornado beendet")