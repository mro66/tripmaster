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
logging.basicConfig(filename = tripmasterPath+"/out/tripmaster.log", format="%(asctime)s.%(msecs)03d - line %(lineno)d - %(levelname)s - %(message)s", datefmt="%d.%m.%Y %H:%M:%S", level=logging.WARNING)

logger = logging.getLogger('Tripmaster')
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.info("Tornado gestartet")
logger.info("DEBUG: " + str(DEBUG))

# Konfigurationseditor
config = configparser.RawConfigParser()
# erhält Groß-/Kleinschreibung
config.optionxform = str
configFileName = tripmasterPath+"/tripmaster.ini"
config.read(configFileName)
# aktive Konfiguration
ACTIVE_CONFIG = config.get("Settings", "aktiv")

# Gestartet?
TRIPMASTER_STARTED = False
# Hat Antriebswellensensor?
HAS_SENSORS = False
# Zeit ist synchronisiert?
IS_TIME_SYNC = False

# Einrichten der BCM GPIO Nummerierung
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
# Messzeitpunkt gesamt und Abschnitt
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
# Zurückgelegte Kilometer - gesamt, Etappe und Abschnitt
KM_TOTAL = 0.0
KM_STAGE = 0.0
KM_SECTOR = 0.0
LAT_PREV = None
LON_PREV = None
KM_TOTAL_GPS = 0.0
KM_STAGE_GPS = 0.0
KM_SECTOR_GPS = 0.0
# Vorgegebene Abschnittslänge
KM_SECTOR_PRESET = 0.0
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

STAGE_NO = 0
STAGE_START = 0
STAGE_FINISH = 0
STAGE_DURATION = 0
SECTOR_NO = 0
SECTORTRACK = None

def getGPS():
    # Aktuelle Position
    GPS_CURRENT = gpsd.get_current()
    # MIndestens ein 2D Fix ist notwendig, sonst zu ungenau
    if GPS_CURRENT.mode >= 2:
        return GPS_CURRENT
    else:
        return None

# Tripmaster initialisieren
def initTripmaster():
    global KML, KML_FILE, STAGE_NO, STAGE_START, STAGE_FINISH, POINTS, INDEX, T, KM_TOTAL, KM_STAGE, KM_SECTOR
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
    STAGE_NO = 0
    STAGE_START = 0
    STAGE_FINISH = 0
    INDEX = 0
    T = 0.0
    KM_TOTAL = 0.0
    KM_STAGE = 0.0
    KM_SECTOR = 0.0
    logger.debug("initTripmaster")

# Etappe initialisieren
def initStage(LON, LAT):
    global FOLDERS, SECTOR_NO, STAGE_NO, KM_STAGE
    STAGE_NO += 1
    FOLDERS["stage"] = KML.newfolder(name="Etappe " + str(STAGE_NO))
    FOLDERS["sectortrack"] = FOLDERS["stage"].newfolder(name="Abschnitte")
    FOLDERS["countpoint"] = FOLDERS["stage"].newfolder(name="Zählpunkte")
    FOLDERS["checkpoint"] = FOLDERS["stage"].newfolder(name="Orientierungskontrollen")
    KM_STAGE = 0.0
    SECTOR_NO = 0
    setPoint(FOLDERS["stage"], POINTS["stage_start"].style, LON, LAT, "", POINTS["stage_start"].name)
    logger.debug("initStage")
    initSector(LON, LAT)

# Abschnitt initialisieren
def initSector(LON, LAT):
    global KML_FILE, SECTOR_NO, SECTORTRACK, T_SECTOR, KM_SECTOR, KM_SECTOR_PRESET, REVERSE
    if SECTOR_NO > 1:
        # Alten Abschnitt mit den aktuellen Koordinaten abschließen
        SECTORTRACK.coords.addcoordinates([(LON,LAT)])
        KML.savekmz(KML_FILE)
    SECTOR_NO += 1
    SECTORTRACK = FOLDERS["sectortrack"].newlinestring(name="Abschnitt "+str(SECTOR_NO))
    if (SECTOR_NO % 2 == 0):
        SECTORTRACK.style = TRACK_RED
    else:
        SECTORTRACK.style = TRACK_GREEN
    SECTORTRACK.coords.addcoordinates([(LON,LAT)])
    KML.savekmz(KML_FILE)
    T_SECTOR = 0.0
    KM_SECTOR = 0.0
    KM_SECTOR_PRESET = 0.0
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
    global IS_TIME_SYNC
    if (len(GPS_CURRENT.time) == 24):
        naive = datetime.strptime(GPS_CURRENT.time, '%Y-%m-%dT%H:%M:%S.%fZ')
        utc = tz_utc.localize(naive)
        local = utc.astimezone(tz_berlin)
        subprocess.call("sudo date -u -s '"+str(local)+"' > /dev/null 2>&1", shell=True)
        IS_TIME_SYNC = True

def getData():
    global HAS_SENSORS, N_SENSORS, INDEX, T_SECTOR, KM_TOTAL, KM_STAGE, KM_SECTOR, KM_SECTOR_PRESET, REVERSE, AVG_KMH, AVG_KMH_PRESET
    global KM_TOTAL_GPS, KM_STAGE_GPS, KM_SECTOR_GPS, LAT_PREV, LON_PREV
    global SECTORTRACK, STAGE_DURATION, STAGE_FINISH

    # Ein 0 V Potential an einem der GPIO Pins aktiviert die Antriebswellensensoren
    if ((GPIO.input(GPIO_PIN_1) == 0) or (GPIO.input(GPIO_PIN_2) == 0)) and not HAS_SENSORS:
        HAS_SENSORS = True
        logger.info("Antriebswellensensor(en) automatisch aktiviert!")

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

    # MIndestens ein 2D Fix ist notwendig, sonst zu ungenau
    if GPS_CURRENT.mode >= 2:

        # KMH_GPS = GPS_CURRENT.speed() * 3.6 - gibt auf einmal nur noch 0.0 zurück
        if (GPS_CURRENT.hspeed > 1.0) and (STAGE_START > 0):
            KMH = GPS_CURRENT.hspeed * 3.6

        KMH_GPS = KMH

        if DEBUG:
            KMH_GPS = 0.1
            LAT = GPS_CURRENT.lat + INDEX/5000
            LON = GPS_CURRENT.lon + INDEX/5000
        else:
            LAT = GPS_CURRENT.lat
            LON = GPS_CURRENT.lon

        if (LAT_PREV is not None) and (LON_PREV is not None) and (KMH_GPS > 0.0) and (STAGE_START > 0):
            DIST = calcGPSdistance(LAT_PREV, LAT, LON_PREV, LON)

        if DEBUG and (STAGE_START > 0):
            MS = DIST * 1000
            KMH_GPS = MS * 3.6
            KMH = KMH_GPS

        LAT_PREV = LAT
        LON_PREV = LON
        KM_TOTAL += DIST
        KM_TOTAL_GPS = KM_TOTAL
        KM_STAGE += DIST * REVERSE
        KM_STAGE_GPS = KM_STAGE
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

        # UMIN ermitteln
        UMIN = int(UMIN_READER_1.RPM() + 0.5)
        if N_SENSORS > 1:
            UMIN += int(UMIN_READER_2.RPM() + 0.5)
            UMIN = UMIN / 2
        #... ohne Sensor
        # UMIN = 2000 + math.sin((T * 5)/180 * math.pi) * 1000
        # Geschwindigkeit in Meter pro Sekunde
        if (STAGE_START > 0):
            MS = UMIN / TRANSMISSION_RATIO / 60 * TYRE_SIZE

        # Geschwindigkeit in Kilometer pro Stunde
        KMH = MS * 3.6
        # Zurückgelegte Kilometer - Gesamt, Etappe und Abschnitt (Rückwärtszählen beim Umdrehen außer bei Gesamt)
        KM_TOTAL += MS * SAMPLE_TIME / 1000
        KM_STAGE += MS * SAMPLE_TIME / 1000 * REVERSE
        KM_SECTOR += MS * SAMPLE_TIME / 1000 * REVERSE

    # Messzeitpunkte Abschnitt
    if (STAGE_START > 0):
        T_SECTOR += SAMPLE_TIME

    # % zurückgelegte Strecke im Abschnitt
    FRAC_SECTOR_DRIVEN = 0
    if KM_SECTOR_PRESET > 0:
        FRAC_SECTOR_DRIVEN = int(min(KM_SECTOR / KM_SECTOR_PRESET * 100, 100))
    # noch zurückzulegende Strecke im Abschnitt (mit der 0.005 wird der Wert 0 in der TextCloud vermieden)
    KM_SECTOR_PRESET_REST = max(KM_SECTOR_PRESET - KM_SECTOR, 0) #0.005)

    # Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
    DEV_AVG_KMH = 0.0

    if T_SECTOR > 0.0:
        # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde im Abschnitt
        AVG_KMH = KM_SECTOR * 1000 / T_SECTOR * 3.6
        if AVG_KMH_PRESET > 0.0:
            DEV_AVG_KMH = AVG_KMH - AVG_KMH_PRESET

    STAGE_RESTTIME = -999999
    STAGE_FRACTIME = 0.0
    if (STAGE_START > 0):
        # Alle 5 Durchläufe Geodaten abspeichern
        # Bounding Box von Deutschland: (5.98865807458, 47.3024876979, 15.0169958839, 54.983104153)),
        if (INDEX % 5 == 0) and IS_TIME_SYNC and 15.1 > LON > 5.9 and 55.0 > LAT > 47.3:
            # geostring = "{0:%d.%m.%Y %H:%M:%S};{1:};{2:};{3:0.1f};{4:0.2f};{5:0.2f};{6:0.2f};{7:0.1f};{8:0.2f};{9:0.2f};{10:0.2f}\n".format(TIME, LAT, LON, KMH, KM_TOTAL, KM_STAGE, KM_SECTOR, KMH_GPS, KM_TOTAL_GPS, KM_STAGE_GPS, KM_SECTOR_GPS)
            # with open(csvFile, 'a+') as datafile:
                # datafile.write(geostring)
            SECTORTRACK.coords.addcoordinates([(LON,LAT)])
            KML.savekmz(KML_FILE)

        if STAGE_FINISH > 0:
            STAGE_RESTTIME = STAGE_FINISH - int(time.time())
            STAGE_FRACTIME = round((1 - STAGE_RESTTIME / STAGE_DURATION) * 100)

    datastring = "data:{0:}:{1:0.1f}:{2:0.1f}:{3:0.1f}:{4:0.2f}:{5:0.2f}:{6:0.2f}:{7:0.2f}:{8:0.2f}:{9:}:{10:0.1f}:{11:}:{12:}:{13:}:{14:}:{15:}:{16:}:{17:}:{18:}".format(INDEX, UMIN, KMH, AVG_KMH, KM_TOTAL, KM_STAGE, KM_SECTOR, KM_SECTOR_PRESET, KM_SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, DEV_AVG_KMH, GPS_CURRENT.mode, LAT, LON, int(HAS_SENSORS), int(IS_TIME_SYNC), int(STAGE_START > 0), int(STAGE_FRACTIME), STAGE_RESTTIME)

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
    global TRIPMASTER_STARTED
    TRIPMASTER_STARTED = True
    timed = threading.Timer(SAMPLE_TIME, pushSpeedData, [client.wsClients, "getData", "{:.1f}".format(SAMPLE_TIME)] )
    timed.start()
    timers.append(timed)
    messageToAllClients(client.wsClients, "Tripmaster gestartet!:success")

def stopTripmaster(client):
    global TRIPMASTER_STARTED
    for index, timer in enumerate(timers):
        if timer:
            timer.cancel()
    TRIPMASTER_STARTED = False
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
    global TRIPMASTER_STARTED
    # Array der WebSocket Clients
    wsClients = []
    CHECKPOINTS = []
    COUNTPOINTS = []

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
            # Verbinden mit pigpio
            pi = pigpio.pi()
            # UMIN_READER starten
            UMIN_READER_1 = reader(pi, GPIO_PIN_1, PULSES_PER_REV)
            UMIN_READER_2 = reader(pi, GPIO_PIN_2, PULSES_PER_REV)
            initTripmaster()
            startTripmaster(self)
            logger.info("Erster WebSocket Client verbunden")

        for b in range(4):
            button = "button-" + str(b+1)
            config.read(configFileName)
            buttonconfig = config.get("Settings", button)
            buttonconfigsplit = buttonconfig.split(":")
            pointCategory = buttonconfigsplit[0]
            pointType = buttonconfigsplit[1]
            self.write_message("::setButtons#" + button + "#" + POINTS[pointType].icon + "#" + POINTS[pointType].iconcolor + "#" + pointCategory + "#" + pointType)

        stagestatus = "stage_start"
        if STAGE_START == 0:
            stagestatus = "stage_finish"
        messageToAllClients(self.wsClients, "::setButtons#button-togglestage#" + POINTS[stagestatus].icon + "#" + POINTS[stagestatus].iconcolor + "#toggleStage#")

        logger.info("Anzahl verbundener WebSocket Clients: " + str(len(self.wsClients)))

    # the client sent a message
    def on_message(self, message):
        global TRIPMASTER_STARTED, ACTIVE_CONFIG
        global INDEX, T, T_SECTOR, KM_TOTAL, KM_STAGE, KM_SECTOR, KM_SECTOR_PRESET, REVERSE, COUNTDOWN, AVG_KMH_PRESET
        global KML, FOLDERS
        global STAGE_START, STAGE_FINISH, STAGE_DURATION
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
            if TRIPMASTER_STARTED == True:
                currentPos = getGPS();
                if currentPos is not None:
                    initSector(currentPos.lon, currentPos.lat)
                    messageToAllClients(self.wsClients, "Abschnittszähler zurückgesetzt!:success:sectorReset")
                else:
                    messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")
            else:
                messageToAllClients(self.wsClients, "Tripmaster noch nicht gestartet!:warning")

        # Abschnittslänge setzen
        elif command == "setSectorLength":
            KM_SECTOR_PRESET = float(param)
            messageToAllClients(self.wsClients, "Abschnitt auf "+locale.format("%.2f", KM_SECTOR_PRESET)+" km gesetzt!:success:sectorLengthset")
        
        # Verfahren
        elif command == "toggleReverse":
            REVERSE = REVERSE * -1
            if REVERSE == -1:
                messageToAllClients(self.wsClients, "Verfahren! km-Zähler rückwärts:warning")
            else:
                messageToAllClients(self.wsClients, "km-Zähler wieder normal:success")

        # Etappe
        elif command == "toggleStage":
            currentPos = getGPS();
            if currentPos is not None:
                if (STAGE_START == 0):
                    STAGE_START = int(time.time()) #datetime.timestamp(datetime.now()))
                    initStage(currentPos.lon, currentPos.lat)                    
                    messageToAllClients(self.wsClients, "Etappe gestartet:success:setButtons#button-togglestage#" + POINTS["stage_start"].icon + "#" + POINTS["stage_start"].iconcolor + "#toggleStage#")
                else:
                    STAGE_START = 0
                    setPoint(FOLDERS["stage"], POINTS["stage_finish"].style, currentPos.lon, currentPos.lat, "", POINTS["stage_finish"].name)
                    messageToAllClients(self.wsClients, "Etappe beendet:success:setButtons#button-togglestage#" + POINTS["stage_finish"].icon + "#" + POINTS["stage_finish"].iconcolor + "#toggleStage#")
            else:
                messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")
        elif command == "setStageTime":
            if param == 'null':
                STAGE_FINISH = 0
                messageToAllClients(self.wsClients, "Etappenzielzeit gelöscht:success")
            else:
                STAGE_FINISH = int(int(param) / 1000)
                STAGE_DURATION = STAGE_FINISH - int(time.time())
                if STAGE_DURATION > 0:
                    messageToAllClients(self.wsClients, "Etappenzielzeit gesetzt:success")
                else:
                    STAGE_FINISH = 0

    # Gleichmäßigkeitsprüfung
        elif command == "startRegtest":
            COUNTDOWN = int(param)
            startRegtest(self)
            messageToAllClients(self.wsClients, "GLP gestartet:success:regTestStarted")
        elif command == "setRegtestLength":
            KM_SECTOR_PRESET = float(param)
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
        
        # Tripmaster
        elif command == "resetTripmaster":
            self.CHECKPOINTS.clear()
            self.COUNTPOINTS.clear()
            KML = simplekml.Kml(open=1)
            initTripmaster()
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

        # Buttons definieren
        elif (command.startswith("button")):
            button = command
            buttonNo = button.replace("button-", "")
            pointCategory = param
            pointType = messagesplit[2]
            # In ini abspeichern
            config.set("Settings", button, pointCategory+":"+pointType)
            with open(configFileName, "w") as configfile:    # save
                config.write(configfile)
            messageToAllClients(self.wsClients, "Button " + buttonNo + " als '" + POINTS[pointType].name + "' definiert:success:setButtons#" + button + "#" + POINTS[pointType].icon + "#" + POINTS[pointType].iconcolor + "#" + pointCategory + "#" + pointType)
        
        # Punkte registrieren
        elif (command == "countpoint") or (command == "checkpoint"):
            currentPos = getGPS();
            if currentPos is not None:
                NEWPOINT = setPoint(FOLDERS[command], POINTS[param].style, currentPos.lon, currentPos.lat, POINTS[param].name)
                if command == "countpoint":
                    self.COUNTPOINTS.append(NEWPOINT)
                    id = self.COUNTPOINTS.index(NEWPOINT)
                elif command == "checkpoint":
                    self.CHECKPOINTS.append(NEWPOINT)
                    id = self.CHECKPOINTS.index(NEWPOINT)
                messageToAllClients(self.wsClients, POINTS[param].name + " registriert:success:" + command + "Registered#" + str(id) + "#" + POINTS[param].name + "##1")
            else:
                messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")

        # Punkte ändern
        elif command == "changepoint":
            paramsplit = param.split("&")
            id = int(paramsplit[1])
            description = paramsplit[2]
            name = paramsplit[3]
            visibility = int(paramsplit[4])
            # Parameter des Punktes ändern
            if paramsplit[0] == "countpoint":
                self.COUNTPOINTS[id].visibility = visibility
                self.COUNTPOINTS[id].style = getStyleByName(description, visibility)
            elif paramsplit[0] == "checkpoint":
                self.CHECKPOINTS[id].visibility = visibility
                self.CHECKPOINTS[id].style = getStyleByName(description, visibility)
                self.CHECKPOINTS[id].name = name
                self.CHECKPOINTS[id].description = description
            KML.savekmz(KML_FILE)
            self.write_message("ID " + str(id) + " - " + description + " geändert:success")

        # Alle Punkte beim Start laden
        elif command == "getAllPoints":
            for COUNTPOINT in self.COUNTPOINTS:
                id = self.COUNTPOINTS.index(COUNTPOINT)
                description = COUNTPOINT.description
                name = COUNTPOINT.name
                visibility = COUNTPOINT.visibility
                self.write_message("::countpointRegistered#" + str(id) + "#" + description + "#" + name + "#" + str(visibility))
            for CHECKPOINT in self.CHECKPOINTS:
                id = self.CHECKPOINTS.index(CHECKPOINT)
                description = CHECKPOINT.description
                name = CHECKPOINT.name
                visibility = CHECKPOINT.visibility
                self.write_message("::checkpointRegistered#" + str(id) + "#" + description + "#" + name + "#" + str(visibility))

        else:
            self.write_message("Unbekannter Befehl - " + command + ":error")

    # Client getrennt
    def on_close(self):
        # Aus der Liste laufender Clients entfernen
        self.wsClients.remove(self)

        if len(self.wsClients) == 0:
            # UMIN_READER stoppen
            UMIN_READER_1.cancel()
            UMIN_READER_2.cancel()
            # Verbindung mit pigpio beenden
            pi.stop()

            # Tripmaster stoppen
            stopTripmaster(self)
            logger.info("Letzter WebSocket Client getrennt")

        logger.info("Anzahl verbundener Clients: " + str(len(self.wsClients)))

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