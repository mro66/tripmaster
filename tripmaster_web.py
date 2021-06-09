#!/usr/bin/env python3

from __future__ import print_function
from datetime import datetime
from gpiozero import CPUTemperature, DigitalInputDevice, DigitalOutputDevice, LED
from ina219 import INA219       
from logging.handlers import RotatingFileHandler
from psutil import cpu_percent, virtual_memory
from read_RPM import reader
from tornado.options import options
from tornado.platform.asyncio import AsyncIOMainLoop
import asyncio
import configparser
import copy
import csv
import glob
import gpsd
import locale
import logging
import math
import os.path
import pickle
import pigpio
import pytz
import simplekml
import subprocess
import sys
import threading
import time
import tornado.web
import tornado.websocket
import tornado.httpserver
# import tornado.ioloop

#-------------------------------------------------------------------

### --- Konfiguration DEBUG ---
DEBUG = False
# Kommandozeilenargument
if len(sys.argv) > 1:
    DEBUG = (sys.argv[1] == "debug")
DEBUG_GPS_INDEX = 0

### --- Konfiguration Tornado ---
WebServer = None
WebsocketServer = None
WebsocketPort = 7070
timerThreadStarted = False

### --- Konfiguration Tripmaster ---
# Komma als Dezimaltrennzeichen
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
# Zeitzonen
tz_utc = pytz.timezone('UTC')
tz_berlin = pytz.timezone('Europe/Berlin')

### --- Konfiguration Logger/Output ---
# Programmpfad für Dateiausgaben
tripmasterPath = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    handlers=[RotatingFileHandler(tripmasterPath+"/out/tripmaster.log", maxBytes=500000, backupCount=5)],
    format="%(asctime)s.%(msecs)03d - line %(lineno)d - %(levelname)s - %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S")
logger = logging.getLogger('Tripmaster')
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

rallyeFile = tripmasterPath + '/out/rallye.dat'
trackFile  = tripmasterPath + '/out/track.csv'
outputFile = tripmasterPath + '/out/output.txt'

### Konfiguration Antriebswellensensor(en)
# GPIO Pins der Sensoren
GPIO_PIN_1 = 17 # weiß
GPIO_PIN_2 = 18 # blau

# DigitalInputDevice setzt standardmäßig pull_up=False, d.h. is_active ist True, wenn Pin ist HIGH
# Reedsensor 1 an Pin 17 (weiß)
REED1 = DigitalInputDevice(GPIO_PIN_1, pull_up=True)
# Reedsensor 2 an Pin 18 (blau)
REED2 = DigitalInputDevice(GPIO_PIN_2, pull_up=True)

# DigitalOutputDevice setzt standardmäßig active_high=True (on() -> HIGH) und initial_value=False (device ist aus)
# Der Lüfter an Pin 27 
FAN = DigitalOutputDevice(27)

# Zweifarbige Status-LED
# Rot beim Start ausschalten...
LED_RED = LED(26, initial_value=False)
# ... und Grün blinkend ein, bis ein Client sich verbindet
LED_GREEN = LED(19, initial_value=True)
LED_GREEN.blink()

# Verbindung zu pigpio Deamon
pi = None
# Die UMIN_READER
UMIN_READER_1 = None
UMIN_READER_2 = None
# Impulse pro Umdrehung
PULSES_PER_REV = 1.0

### GPS Deamon
gpsd.connect()

### Spannungsmessung
SHUNT_RESISTANCE = 0.1
MAX_CURRENT = 0.4
ina = INA219(SHUNT_RESISTANCE, MAX_CURRENT)
ina.configure(ina.RANGE_16V, ina.GAIN_1_40MV)

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

# Messen alle ... Sekunden
SAMPLE_TIME = 1.0
# Zeit ist synchronisiert?
IS_TIME_SYNC = None
# Hat Antriebswellensensor?
HAS_SENSORS = False
# Durchschnittsgeschwindigkeit - aktuell und Vorgabe
AVG_KMH = 0.0
AVG_KMH_PRESET = 0.0
# Zeitvorgabe der GLP
COUNTDOWN = 0

# Fortlaufender Index
INDEX = 0
# Rallye
RALLYE = None
# Etappe
STAGE  = None
# Abschnitt
SECTOR = None

# Parameter des RasPi (Listen, damit gleitende Mittel berechnet werden können)
class PI_PARAMS:
    def __init__(self):
        self.MEM_USED = 0
        self.STACK_MEM_USED = []
        self.CPU_LOAD = 0
        self.STACK_CPU_LOAD = []
        self.CPU_TEMP = 0
        self.STACK_CPU_TEMP = []
        self.UBAT = 0
        self.STACK_UBAT = []

    def setStatus(self):
        # CPU Auslastung in %
        self.CPU_LOAD = self.movingAverage(self.STACK_CPU_LOAD, cpu_percent(), 20)
        # CPU Temperatur in °C
        self.CPU_TEMP = self.movingAverage(self.STACK_CPU_TEMP, CPUTemperature().temperature, 20)
        # Speicherauslastung in %
        self.MEM_USED = self.movingAverage(self.STACK_MEM_USED, virtual_memory().available / virtual_memory().total * 100, 10)
        # Akkuspannung in V
        ubat = self.movingAverage(self.STACK_UBAT, ina.voltage() + ina.shunt_voltage()/1000, 20)
        # Wenn die Spannungsmessung weniger als 2V liefert, ist _wahrscheinlich_ ein Netzteil am USB Port
        # (sonst würde der Pi nicht laufen)
        if ubat < 2.0:
            ubat = 5.0
        self.UBAT = min(ubat, 5.0)

    def movingAverage(self, stack, newval, maxlength):
        # Neuen Wert am Ende des Stacks einfügen
        stack.append(newval)
        if len(stack) > maxlength:
            # Erstes Element entfernen, wenn maximale Länge des Stacks überschritten wird
            stack.pop(0)
        # Mittelwert des Stacks zurückgeben
        return sum(stack) / len(stack)

PI_STATUS = PI_PARAMS()
# UBAT_CAP * 25 = % Akkukapazität
UBAT_CAP = 0

class POINT_ATTR:
    def __init__(self, name, icon, iconcolor):
        self.name = name
        self.icon = icon
        self.iconcolor = "var(--tm-" + iconcolor + ")"

# POINTS sind vom Typ Dictionary: Der KEY ist der subtype, die VALUES vom Typ List mit name, icon, iconcolor
POINTS = {
    # Etappenstart und -ziel
    "stage_start" : POINT_ATTR("Start Etappe", "fas fa-flag-checkered", "red"),
    "stage_finish": POINT_ATTR("Ende Etappe", "fas fa-flag-checkered", "green"),
    # Zählpunkte und Orientierungskontrollen
    "roundabout"  : POINT_ATTR("Kreisverkehr", "fas fa-sync", "blue"),
    "townsign"    : POINT_ATTR("Ortsschild", "fas fa-sign", "yellow"),
    "stampcheck"  : POINT_ATTR("Stempelkontrolle", "fas fa-stamp", "red"),
    "mutecheck"   : POINT_ATTR("Stummer Wächter", "fas fa-neuter", "green"),
    "countpoint"  : POINT_ATTR("Sonstiges", "fas fa-hashtag", "blue"),
    "checkpoint"  : POINT_ATTR("Sonstige OK", "fas fa-map-marker-alt", "green"),
    # Sonstige
    "null"        : POINT_ATTR("Inaktiv", "fas fa-question", "lightgray"),
     }

class POINT:
    def __init__(self, lon, lat, ptype = None, subtype = None):
        self.id     = None
        self.lon    = lon
        self.lat    = lat
        self.value  = None       # z. B. Buchstabe von Ortsschildern
        self.active = 1
        if (ptype != None):
            self.type    = ptype
            self.subtype = subtype
        else:
            self.type = "track"

# Rallye, Etappe und Abschnitt sind SECTIONs
class SECTION:
    def __init__(self, parent):
        if (parent == None):
            parent_id = -1
        else:
            parent_id = parent.id
        self.parent_id   = parent_id
        self.id          = None     # Index, bei subsections die Position in der Liste
        self.t           = 0.0      # Messpunkt
        self.autostart   = False    # Startzeit einer Etappe ist eingerichtet
        self.start       = 0        # Startzeit
        self.finish      = 0        # Zielzeit
        self.preset      = 0.0      # Streckenvorgabe
        self.reverse     = 1        # km-Zähler läuft ... 1 = normal, -1 = rückwärts
        self.km          = 0.0      # Strecke
        self.km_gps      = 0.0      # Strecke (GPS)
        self.points      = []       # Start/Ende bei Etappen, Trackpunkte bei Abschnitten
        self.countpoints = []       # Zählpunkte bei Etappen
        self.checkpoints = []       # Orientierungskontrollen bei Etappen
        self.subsection  = []       # Untersektionen (Etappen bei Rallye, Abschnitte bei Etappen)

    def getDuration(self):
        if (self.start > 0) and (self.finish > 0):
            return max(self.finish - self.start, 0)
        else:
            return 0

    def isStarted(self):
        return ((self.start > 0) and (self.start <= int(datetime.timestamp(datetime.now()))))

    def setAutostart(self, autostart, start):
        self.autostart = autostart
        self.start     = start

    def startStage(self, rallye, lon, lat):
        newstage       = SECTION(rallye)
        newstage.start = datetime.timestamp(datetime.now())
        newstage.km    = 0.0
        rallye.subsection.append(newstage)
        newstage.id    = rallye.subsection.index(newstage)
        logger.debug("   Etappe " + str(newstage.id) + " gestartet: " + locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat))
        newstage.setPoint(lon, lat, "stage", "stage_start")
        return newstage

    def endStage(self, lon, lat):
        self.start = 0
        self.setPoint(lon, lat, "stage", "stage_finish")
        logger.debug("   Etappe " + str(self.id) + " gestoppt:  " + locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat))

    def startSector(self, stage, lon, lat):
        newsector = SECTION(stage)
        stage.subsection.append(newsector)
        newsector.id = stage.subsection.index(newsector)
        newsector.setPoint(lon, lat, "sector", "sector_start")
        logger.debug("Abschnitt " + str(newsector.id) + " gestartet: " + locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat))
        return newsector

    def endSector(self, lon, lat):
        self.setPoint(lon, lat, "sector", "sector_finish")
        logger.debug("Abschnitt " + str(self.id) + " gestoppt:  " + locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat))

    def setPoint(self, lon, lat, ptype, subtype):
        # Bounding Box von Deutschland: (5.98865807458, 47.3024876979, 15.0169958839, 54.983104153)),
        # if (15.1 > lon > 5.9) and (55.0 > lat > 47.3):
        newPoint = POINT(lon, lat, ptype, subtype)
        if (ptype == 'countpoint'):
            self.countpoints.append(newPoint)
            newPoint.id = self.countpoints.index(newPoint)
        elif (ptype == 'checkpoint'):
            self.checkpoints.append(newPoint)
            newPoint.id = self.checkpoints.index(newPoint)
        elif (ptype == 'stage'):
            self.points.append(newPoint)
            newPoint.id = self.points.index(newPoint)
        # Trackpoints
        elif (ptype == 'sector'):
            if (len(self.points) > 0):
                self.points.pop(0)
            self.points.append(newPoint)
            newPoint.id = self.points.index(newPoint) # ist immer 0!
            # in TrackCSV speichern
            with open(trackFile, 'a') as tf:
                trackWriter = csv.writer(tf)
                trackWriter.writerow([self.parent_id, self.id, lon, lat])
#             logger.debug("Trackpunkt " + str(newPoint.id) + ": " + locale.format_string("%.4f", lon) + "/" + locale.format_string("%.4f", lat))
#             logger.debug("parent.id: {0:}, self.id: {1:}, lon: {2:0.4f}, lat {3:0.4f} ".format(self.parent_id, self.id, lon, lat))

        else:
            logger.error("Unbekannter oder fehlender Punkttyp (ptype)")
        pickleData()
        return newPoint.id

    def changePoint(self, ptype, i, active, value):
        if ptype == "countpoint":
            self.countpoints[i].active = active
        elif ptype == "checkpoint":
            self.checkpoints[i].active = active
            self.checkpoints[i].value = value
        pickleData()

    # Nur für Abschnitt/SECTOR: Holt Koordinate des letzten Listeneintrags
    def getLon(self):
        if len(self.points) > 0:
            return self.points[-1].lon
        else:
            return None
    def getLat(self):
        if len(self.points) > 0:
            return self.points[-1].lat
        else:
            return None

    # Gibt beim Daten laden die letzte subsection zurück
    def getLastSubsection(self):
        if (len(self.subsection) > 0):
            return self.subsection[-1]
        else:
            return SECTION(RALLYE)

def pickleData():
    with open(rallyeFile, 'wb') as fp:
        pickle.dump(RALLYE, fp)

def unpickleData():
    if os.path.exists(rallyeFile) and (os.path.getsize(rallyeFile) > 0):
        try:
            with open(rallyeFile, 'rb') as fp:
                return pickle.load(fp)
        except EOFError:
            logger.error("EOFError!")
    return None

def saveOutput(var):
    with open(outputFile, 'a') as of:
        of.write('{:}'.format(datetime.now().strftime('%d.%m.%Y %H:%M:%S')))
        for v in var:
            of.write('\t{:0.4f}'.format(v).replace('.', ','))
        of.write('\n')

# ----------------------------------------------------------------

def saveKMZ(rallye):
    
    start_time = time.time()

    KML = simplekml.Kml(open=1, \
                        description="Länge der Rallye: " + locale.format_string("%.1f", rallye.km) + " km")
    
    # Set aller genutzten POINT subtypes, Sets haben keine(!) Duplikate
    subtypes = set();

    # RALLYE und SECTOR haben keine Punkte (SECTOR hat nur Tracks)
    for stage in rallye.subsection:
        # Etappebeginn, -ende
        for p in stage.points:
            subtypes.add(p.subtype)
        # Zählpunkte
        for p in stage.countpoints:
            subtypes.add(p.subtype)
        # Orientierungskontrollen
        for p in stage.checkpoints:
            subtypes.add(p.subtype)

    # Nur die Styles für die genutzten POINT subtypes definieren
    styles = {};
    for s in subtypes:
        icon = tripmasterPath + "/static/kmz/" + s + ".gif"
        styles[s] = simplekml.Style()
        styles[s].iconstyle.icon.href = KML.addfile(icon)

    # Styles für Tracks
    styles["track0"] = simplekml.Style()
    styles["track0"].linestyle.width = 5
    styles["track0"].linestyle.color = "ff4f53d9"  # rot
    styles["track1"] = simplekml.Style()
    styles["track1"].linestyle.width = 5
    styles["track1"].linestyle.color = "ff5cb85c"  # grün

    logger.debug("KML Vorbereitung --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()

    # Eine deepcopy des RALLYE Objektes erstellen, da die POINTS der Abschnitte zum Ausgeben überschrieben werden
    r = copy.deepcopy(rallye)

    logger.debug("deepcopy des RALLYE Objektes erstellen --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()

    # Gespeicherte POINTS in den Abschnitten löschen
    for stage in r.subsection:
        for sector in stage.subsection:
            sector.points.clear()    

    logger.debug("Gespeicherte POINTS in den Abschnitten löschen --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    # Inhalt der TrackCSV in eine Liste kopieren
    with open(trackFile) as csv_file:
        tracks = list(csv.reader(csv_file))
        
    logger.debug("Inhalt der TrackCSV in eine Liste kopieren --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    # POINTS in die Abschnitte kopieren
    for row in tracks:
        stage_id = int(row[0])
        sector_id = int(row[1])
        lon = float(row[2])
        lat = float(row[3])
        for stage in r.subsection:
            for sector in stage.subsection:
                if (stage.id == stage_id) and (sector.id == sector_id):
                    newPoint = POINT(lon, lat, "sector", "track")
                    sector.points.append(newPoint)

    logger.debug("POINTS in die Abschnitte kopieren --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    for stage in r.subsection:

        sf = KML.newfolder(name="Etappe " + str(stage.id+1))
        for p in stage.points:
            # 'name' ist der label, 'description' erscheint darunter
            newpoint = sf.newpoint(coords = [(p.lon, p.lat)], \
                                   name = POINTS[p.subtype].name, \
                                   description = "Länge: " + locale.format_string("%.2f", stage.km) + " km")
            newpoint.style = styles[p.subtype]

        f = sf.newfolder(name="Abschnitte")
        for sector in stage.subsection:
            newtrack = f.newlinestring(name = "Abschnitt "+str(sector.id+1), \
                                       description = "Länge: " + locale.format_string("%.2f", sector.km) + " km")
            newtrack.style = styles["track"+str(sector.id % 2)]
            for p in sector.points:
                newtrack.coords.addcoordinates([(p.lon, p.lat)])

        if len(stage.countpoints) > 0:
            f = sf.newfolder(name="Zählpunkte")
            # Nur aktive Punkte werden gespeichert
            for p in (x for x in stage.countpoints if x.active == 1):
                newpoint = f.newpoint(coords = [(p.lon, p.lat)], \
                                      description = POINTS[p.subtype].name)
                newpoint.style = styles[p.subtype]

        if len(stage.checkpoints) > 0:
            f = sf.newfolder(name="Orientierungskontrollen")
            for p in (x for x in stage.checkpoints if x.active == 1):
                newpoint = f.newpoint(coords = [(p.lon, p.lat)], \
                                      name = p.value, \
                                      description = POINTS[p.subtype].name)
                newpoint.style = styles[p.subtype]

    logger.debug("KML erstellen --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    KML_FILE = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.kmz".format(datetime.now());
    KML.savekmz(KML_FILE)

    logger.debug("KMZ speichern --- %s seconds ---" % (time.time() - start_time))
    
    now = time.time()
    # Maximal fünf Sekunden warten
    last_time = now + 5
    while time.time() <= last_time:
        if os.path.exists(KML_FILE):
            return True
        else:
            # Eine halbe Sekunde warten, dann wieder prüfen
            time.sleep(0.5)
    return False

# ----------------------------------------------------------------

def prettyprint(rallye):
    print('------ prettyprint(rallye) ---------------')
    # eine deepcopy des RALLYE Objektes erstellen, da die POINTS der Abschnitte zum Ausgeben überschrieben werden
    r = copy.deepcopy(rallye)

    # Gespeicherte POINTS in den Abschnitten löschen
    for stage in r.subsection:
        for sector in stage.subsection:
            sector.points.clear()    
    
    # Inhalt der TrackCSV in eine Liste kopieren
    with open(trackFile) as csv_file:
        tracks = list(csv.reader(csv_file))
        
    # POINTS in die Abschnitte kopieren
    for row in tracks:
        stage_id = int(row[0])
        sector_id = int(row[1])
        lon = float(row[2])
        lat = float(row[3])
        for stage in r.subsection:
            for sector in stage.subsection:
                if (stage.id == stage_id) and (sector.id == sector_id):
                    newPoint = POINT(lon, lat, "sector", "track")
                    sector.points.append(newPoint)

    for stage in r.subsection:

        print("Etappe " + str(stage.id+1))
        for p in stage.points:
            print("  name:   " + POINTS[p.subtype].name)
            print("  Länge:  {:0.2f}".format(stage.km) +" km")
            print("  coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))

        for sector in stage.subsection:
            print("  Abschnitt " + str(sector.id+1))
            print("    Länge:  {:0.2f}".format(sector.km) +" km")
            for p in sector.points:
                print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))
 
        if len(stage.countpoints) > 0:
            print("  Zählpunkte")
            for p in (x for x in stage.countpoints if x.active == 1):
                print("    name:   " + POINTS[p.subtype].name)
                print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))
 
        if len(stage.checkpoints) > 0:
            print("  Orientierungskontrollen")
            for p in (x for x in stage.checkpoints if x.active == 1):
                print("    name:   " + POINTS[p.subtype].name)
                if p.value == None:
                    value = "-"
                else:
                    value = p.value
                print("    value:  " + value)
                print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))

# ----------------------------------------------------------------

def startRallye(loadSavedData = True):
    global INDEX, RALLYE, STAGE, SECTOR
    # Daten laden sofern vorhanden
    if loadSavedData == True:
        RALLYE = unpickleData()
        # Gibt es einen Fehler beim Laden, dann gleich neu machen
        if RALLYE == None:
            loadSavedData = False
        else:
            STAGE  = RALLYE.getLastSubsection()
            SECTOR = STAGE.getLastSubsection()

    if loadSavedData == False:
        current_date = "{0:%Y%m%d_%H%M}".format(datetime.now())
        if os.path.exists(rallyeFile):
            os.rename(rallyeFile, tripmasterPath+"/out/"+current_date+".dat")
        if os.path.exists(trackFile):
            os.rename(trackFile, tripmasterPath+"/out/"+current_date+".csv")
        INDEX  = 0
        RALLYE = SECTION(None)
        STAGE  = SECTION(RALLYE)
        SECTOR = SECTION(STAGE)
        # legt leere Rallyedatei an
        pickleData()
        # legt leere TrackCSV an
        open(trackFile, 'a').close()

startRallye()
# if DEBUG: prettyprint(RALLYE)

#-------------------------------------------------------------------

# Schreibt Nachrichten an alle Clients
def messageToAllClients(clients, message):
    for client in clients:      # for index, client in enumerate(clients):
        if client:
            try:
                client.write_message(message)
            except BufferError:
                logger.error("BufferError beim Aussenden einer Message zum Client")

#-------------------------------------------------------------------
### Parse request from client
#required format-> command:param
def WebRequestHandler(requestlist):
    returnlist = ""
    for request in requestlist:
        request      = request.strip()
        requestsplit = request.split(":")
        requestsplit.append("dummy")
        command      = requestsplit[0]
        param        = requestsplit[1]
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
        utc   = tz_utc.localize(naive)
        local = utc.astimezone(tz_berlin)
        subprocess.call("sudo date -u -s '"+str(local)+"' > /dev/null 2>&1", shell=True)
        return True
    else:
        return False

def getGPSCurrent():
    global DEBUG_GPS_INDEX, LED_GREEN
    # Aktuelle Position
    GPS_CURRENT = gpsd.get_current()
    if DEBUG:
        DEBUG_GPS_INDEX   += 1
        GPS_CURRENT.mode   = 3
        GPS_CURRENT.lon = 10.45 + DEBUG_GPS_INDEX/5000
        GPS_CURRENT.lat = 51.16 + DEBUG_GPS_INDEX/7500
        GPS_CURRENT.hspeed = 15
    return GPS_CURRENT

def getData():
    global STAGE, SECTOR, IS_TIME_SYNC, HAS_SENSORS, INDEX, AVG_KMH, PI_STATUS, UBAT_CAP

    # Ein 0 V Potential an einem der beiden Reedsensoren aktiviert die Antriebswellensensoren
    if (REED1.is_active or REED2.is_active) and not HAS_SENSORS:
        HAS_SENSORS = True
        logger.info("Antriebswellensensor(en) automatisch aktiviert!")

    # Index hochzählen
    INDEX  += 1

    # Aktuelle GPS Position
    GPS_CURRENT = getGPSCurrent()
    
    # Berechne gleitende Mittel der Systemparameter...
    PI_STATUS.setStatus()
    # ... Akkuspannung
    UBAT = PI_STATUS.UBAT
    # ... CPU Temperatur
    CPU_TEMP = PI_STATUS.CPU_TEMP
    # ... CPU Auslastung
    CPU_LOAD = PI_STATUS.CPU_LOAD
    # ... Speicherauslastung
    MEM_USED = PI_STATUS.MEM_USED

#     logger.debug("MEM LOAD TEMP BAT: " + "{0:0.2f} {1:0.2f} {2:0.2f} {3:0.2f}".format(MEM_USED, CPU_LOAD, CPU_TEMP, UBAT))

    # Alle 10 Durchläufe Zeit synchronisieren und den RasPi Status abfragen und speichern
    if (INDEX % 10 == 0) or (IS_TIME_SYNC == None):
        IS_TIME_SYNC = DEBUG or syncTime(GPS_CURRENT)

        # Lüfter an bei über 70°C
        if (CPU_TEMP > 70.0):
            FAN.on()
        # Lüfter aus bei unter 58°C
        elif (CPU_TEMP < 58.0):
            FAN.off()

        # UBAT_CAP * 25 = Prozent Akkukapazität
        if (UBAT < 3.20):
            UBAT_CAP -= 1 # abschalten!
        elif (UBAT < 3.27):
            UBAT_CAP = 0 # 0 %
        elif (UBAT < 3.58):
            UBAT_CAP = 1 # 25 %
        elif (UBAT < 3.69):
            UBAT_CAP = 2 # 50 %
        elif (UBAT < 3.85):
            UBAT_CAP = 3 # 75 %
        elif (UBAT < 5.0):
            UBAT_CAP = 4 # 100 %
        else:
            UBAT_CAP = 5 # Netzteil

        if DEBUG:
            saveOutput([MEM_USED, CPU_LOAD, CPU_TEMP, UBAT])

    # Umdrehungen der Antriebswelle(n) pro Minute
    UMIN    = 0.0

    # Geschwindigkeit in Kilometer pro Stunde
    KMH     = 0.0
    AVG_KMH = 0.0
    KMH_GPS = 0.0

    # Gefahrene Distanz in km (berechnet aus Geokoordinaten)
    DIST = 0.0

    # noch zurückzulegende Strecke im Abschnitt
    SECTOR_PRESET_REST = 0.0
    # % zurückgelegte Strecke im Abschnitt
    FRAC_SECTOR_DRIVEN = 0
    # Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
    DEV_AVG_KMH        = 0.0

    # Zeit bis zum Start der Etappe
    STAGE_TIMETOSTART  = 0
    # Zeit bis zum Ende der Etappe
    STAGE_TIMETOFINISH = 0
    # % abgelaufene Zeit bis zum Ende der Etappe
    STAGE_FRACTIME     = 0.0

    # Wenn die Etappe läuft ...
    if STAGE.isStarted():

        # Bei Autostart Etappe starten
        if STAGE.autostart == True:
            # Etappe starten
            STAGE = STAGE.startStage(RALLYE, GPS_CURRENT.lon, GPS_CURRENT.lat)
            # Abschnitt starten
            SECTOR = SECTOR.startSector(STAGE, GPS_CURRENT.lon, GPS_CURRENT.lat)

        # Mindestens ein 2D Fix
        if (GPS_CURRENT.mode >= 2):

            # KMH_GPS = GPS_CURRENT.speed() * 3.6 - gibt auf einmal nur noch 0.0 zurück
            if (GPS_CURRENT.hspeed > 1.0):
                KMH_GPS = GPS_CURRENT.hspeed * 3.6

            if (SECTOR.getLon() is not None) and (SECTOR.getLat() is not None) and (KMH_GPS > 0.0):
                DIST = calcGPSdistance(SECTOR.getLon(), GPS_CURRENT.lon, SECTOR.getLat(), GPS_CURRENT.lat)

            KMH            = KMH_GPS
            RALLYE.km     += DIST
            RALLYE.km_gps  = RALLYE.km
            STAGE.km      += DIST * SECTOR.reverse
            STAGE.km_gps   = STAGE.km
            SECTOR.km     += DIST * SECTOR.reverse
            SECTOR.km_gps  = SECTOR.km
            SECTOR.setPoint(GPS_CURRENT.lon, GPS_CURRENT.lat, "sector", "track")

        ### Antriebswellensensor(en)

        if HAS_SENSORS:

            # UMIN ermitteln
            UMIN = int(UMIN_READER_1.RPM() + 0.5)
            if N_SENSORS > 1:
                UMIN += int(UMIN_READER_2.RPM() + 0.5)
                UMIN  = UMIN / 2
            # Geschwindigkeit in Meter pro Sekunde
            MS = UMIN / TRANSMISSION_RATIO / 60 * TYRE_SIZE

            # Geschwindigkeit in Kilometer pro Stunde
            KMH = MS * 3.6
            # Zurückgelegte Kilometer - Rallye, Etappe und Abschnitt (Rückwärtszählen beim Umdrehen außer bei Rallye)
            RALLYE.km += MS * SAMPLE_TIME / 1000
            STAGE.km  += MS * SAMPLE_TIME / 1000 * SECTOR.reverse
            SECTOR.km += MS * SAMPLE_TIME / 1000 * SECTOR.reverse

        # Messzeitpunkte Abschnitt
        SECTOR.t += SAMPLE_TIME

        if SECTOR.preset > 0:
            FRAC_SECTOR_DRIVEN = int(min(SECTOR.km / SECTOR.preset * 100, 100))
        # noch zurückzulegende Strecke im Abschnitt (mit der 0.005 wird der Wert 0 in der TextCloud vermieden)
        SECTOR_PRESET_REST = max(SECTOR.preset - SECTOR.km, 0) #0.005)

        if SECTOR.t > 0.0:
            # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde im Abschnitt
            AVG_KMH = SECTOR.km * 1000 / SECTOR.t * 3.6
            if AVG_KMH_PRESET > 0.0:
                DEV_AVG_KMH = AVG_KMH - AVG_KMH_PRESET

        if STAGE.getDuration() > 0:
            STAGE_TIMETOFINISH = STAGE.finish - int(datetime.timestamp(datetime.now()))
            STAGE_FRACTIME = round((1 - STAGE_TIMETOFINISH / STAGE.getDuration()) * 100)
    else:
        if STAGE.start > 0:
            STAGE_TIMETOSTART = STAGE.start - int(datetime.timestamp(datetime.now()))

    # Aktuelle Zeit als String HH-MM-SS
    NOW = datetime.now().strftime('%H-%M-%S') # .%f')[:-3]


    datastring = "data:{0:}:{1:0.1f}:{2:0.6f}:{3:0.6f}:{4:}:{5:}:{6:}:{7:}:{8:}:{9:}:{10:0.2f}:{11:0.2f}:{12:0.2f}:{13:}:{14:0.2f}:{15:0.2f}:{16:0.1f}:{17:0.1f}:{18:}:{19:0.2f}:{20:}:{21:0.1f}:{22:0.1f}".format(
        NOW, KMH, GPS_CURRENT.lon, GPS_CURRENT.lat, 
        int(HAS_SENSORS), int(IS_TIME_SYNC), int(STAGE.isStarted()), 
        int(STAGE_FRACTIME), STAGE_TIMETOSTART, STAGE_TIMETOFINISH, 
        SECTOR.km, SECTOR.preset, SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, STAGE.km, RALLYE.km, 
        AVG_KMH, DEV_AVG_KMH, 
        GPS_CURRENT.mode, UBAT, UBAT_CAP, CPU_TEMP, CPU_LOAD)

    return datastring

def calcGPSdistance(lambda1, lambda2, phi1, phi2):
    l1 = math.radians(lambda1)
    l2 = math.radians(lambda2)
    p1 = math.radians(phi1)
    p2 = math.radians(phi2)
    x  = (l2-l1) * math.cos((p1+p2)/2)
    y  = (p2-p1)
    return math.sqrt(x*x + y*y) * 6371

def pushSpeedData(clients, what, when):
    if (UBAT_CAP < -3):
        messageToAllClients(clients, "Akku leer! Fahre RasPi herunter...")
        stopTornado()
        time.sleep(3)
        subprocess.call("sudo shutdown -h now", shell=True)
    else:
        what    = str(what)
        message = WebRequestHandler(what.splitlines());
        messageToAllClients(clients, message)
        now     = datetime.now()
        diff    = now - now.replace(microsecond=20000)
        # f       = 1.0 # math.sqrt(2) # 1.582 * (1 - math.exp(-(now.microsecond/20000))) # math.sqrt(now.microsecond/20000)
        when    = SAMPLE_TIME - diff.total_seconds() # * f  # float(when)
        # logger.debug(now.strftime('%H-%M-%S.%f')[:-3] + "\twhen\t{0:0.6f}\tdiff\t{1:0.3f}".format(when, diff.total_seconds()))
        timed   = threading.Timer( when, pushSpeedData, [clients, what, when] )
        timed.daemon = True
        timed.start()

def startRegtest(client):
    timed = threading.Timer(1.0, pushRegtestData, [client.wsClients, "regTest", "1.0"] )
    timed.daemon = True
    timed.start()

def pushRegtestData(clients, what, when):
    global AVG_KMH_PRESET
    what      = str(what)
    when      = float(when)
    message   = WebRequestHandler(what.splitlines())
    countdown = int(message)
    if countdown == 0:
        messageToAllClients(clients, "countdown:"+message)
        AVG_KMH_PRESET = 0.0
        messageToAllClients(clients, "GLP gestoppt:success:regTestStopped")
    elif countdown > 0:
        messageToAllClients(clients, "countdown:"+message)
        timed = threading.Timer( when, pushRegtestData, [clients, what, when] )
        timed.daemon = True
        timed.start()

### WebSocket server tornado <-> WebInterface
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    # Liste der WebSocket Clients
    wsClients = []

    # Client verbunden
    def check_origin(self, origin):
        return True

    def open(self, page):
        global timerThreadStarted, pi, UMIN_READER_1, UMIN_READER_2
        self.stream.set_nodelay(True)
        # Jeder WebSocket Client wird der Liste wsClients hinzugefügt
        self.wsClients.append(self)
        # Die ID ist der Index in der Liste wsClients
        self.id = "Client #" + str(self.wsClients.index(self) + 1) + " (" + page + ")"
        # Sobald sich mindestens ein Client angemeldet hat, hört die grüne LED auf zu blinken
        LED_GREEN.on()

        
        # Wenn es der Timer Thread noch nicht gestartet ist, alles initialisieren
        if timerThreadStarted == False:
            # Verbinden mit pigpio
            pi = pigpio.pi()
            # UMIN_READER starten
            UMIN_READER_1 = reader(pi, GPIO_PIN_1, PULSES_PER_REV)
            UMIN_READER_2 = reader(pi, GPIO_PIN_2, PULSES_PER_REV)
            # Timer starten
            timed = threading.Timer(SAMPLE_TIME, pushSpeedData, [self.wsClients, "getData", "{:.1f}".format(SAMPLE_TIME)] )
            timed.daemon = True
            timed.start()
            timerThreadStarted = True
            logger.info("Timer Thread gestartet")
            if (DEBUG):
                messageToAllClients(self.wsClients, "Tripmaster DEBUG gestartet!:success")
            else:
                messageToAllClients(self.wsClients, "Tripmaster gestartet!:success")

        # Die Buttondefinition aus der INI-Datei lesen
        for b in range(4):
            button            = "button-" + str(b+1)
            config.read(configFileName)
            buttonconfig      = config.get("Settings", button)
            buttonconfigsplit = buttonconfig.split(":")
            pointCategory     = buttonconfigsplit[0]
            pointType         = buttonconfigsplit[1]
            self.write_message("::setButtons#" + button + "#" + POINTS[pointType].icon + "#" + POINTS[pointType].iconcolor + "#" + pointCategory + "#" + pointType)

        stagestatus = "stage_start"
        if STAGE.start == 0:
            stagestatus = "stage_finish"

        messageToAllClients(self.wsClients, "::setButtons#button-togglestage#" + POINTS[stagestatus].icon + "#" + POINTS[stagestatus].iconcolor + "#toggleStage#")

        logger.info("OPEN - Anzahl verbundener Clients: " + str(len(self.wsClients)))

    # the client sent a message
    def on_message(self, message):
        global ACTIVE_CONFIG, STAGE, SECTOR, COUNTDOWN, AVG_KMH_PRESET
        logger.debug("Nachricht " + self.id + ": " + message + "")
        # command:param
        message      = message.strip()
        messagesplit = message.split(":")
        messagesplit.append("dummyparam")
        command      = messagesplit[0]
        param        = messagesplit[1]
        if param == "dummy":
            param = "0"

    # Strecke
        # Verfahren
        if command == "reverse":
            if param == 'true':
                SECTOR.reverse = -1
                messageToAllClients(self.wsClients, "Verfahren! km-Zähler rückwärts:warning")
            else:
                SECTOR.reverse = 1
                messageToAllClients(self.wsClients, "km-Zähler wieder normal:success")

        # Etappe starten/beenden
        elif command == "toggleStage":
            currentPos = self.getGPS();
            if currentPos is not None:
                if (STAGE.start == 0):
                    # Etappe starten
                    STAGE = STAGE.startStage(RALLYE, currentPos.lon, currentPos.lat)
                    # Abschnitt starten
                    SECTOR = SECTOR.startSector(STAGE, currentPos.lon, currentPos.lat)
                    messageToAllClients(self.wsClients, "Etappe gestartet:success:setButtons#button-togglestage#" + POINTS["stage_start"].icon + "#" + POINTS["stage_start"].iconcolor)
                else:
                    # Abschnitt beenden
                    SECTOR.endSector(currentPos.lon, currentPos.lat)
                    # Etappe beenden
                    STAGE.endStage(currentPos.lon, currentPos.lat)
                    messageToAllClients(self.wsClients, "Etappe beendet:success:setButtons#button-togglestage#" + POINTS["stage_finish"].icon + "#" + POINTS["stage_finish"].iconcolor)
#             if DEBUG: prettyprint(RALLYE)
            
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
                STAGE.setAutostart(False, 0)
                messageToAllClients(self.wsClients, "Etappenstartzeit gelöscht:success:setButtons#button-togglestage#" + POINTS["stage_finish"].icon + "#" + POINTS["stage_finish"].iconcolor)
                messageToAllClients(self.wsClients, "::switchToMain")
            else:
                STAGE.setAutostart(True, int(int(param) / 1000))
                starttime = datetime.fromtimestamp(STAGE.start).strftime("%H&#058;%M")
                messageToAllClients(self.wsClients, "Etappe startet automatisch um " + starttime + " Uhr:success:setButtons#button-togglestage#" + POINTS["stage_start"].icon + "#" + POINTS["stage_start"].iconcolor)
                messageToAllClients(self.wsClients, "::switchToClock")

        # Punkte registrieren
        elif (command == "countpoint") or (command == "checkpoint"):
            currentPos = self.getGPS();
            if currentPos is not None:
                ptype    = command
                subptype = param
                i        = STAGE.setPoint(currentPos.lon, currentPos.lat, ptype, subptype)
                messageToAllClients(self.wsClients, POINTS[subptype].name + " registriert:success:" + ptype + "Registered#" + str(i) + "#" + POINTS[subptype].name + "##1")

        # Punkte ändern
        elif command == "changepoint":
            paramsplit = param.split("&")
            ptype      = paramsplit[0]
            i          = int(paramsplit[1])
            name       = paramsplit[2]
            value      = paramsplit[3]
            active     = int(paramsplit[4])

            STAGE.changePoint(ptype, i, active, value)

            # ID zur Anzeige 1-basiert, im System 0-basiert
            self.write_message("ID " + str(i+1) + " - " + name + " geändert:success")

        # Alle Punkte beim Start laden
        elif command == "getAllPoints":
            for countpoint in STAGE.countpoints:
                # i im System 0-basiert
                i      = countpoint.id
                # or '') konvertiert None in ''
                value  = str(countpoint.value or '')
                name   = POINTS[countpoint.subtype].name
                active = countpoint.active
                self.write_message("::countpointRegistered#" + str(i) + "#" + name + "#" + value + "#" + str(active))
            for checkpoint in STAGE.checkpoints:
                i      = checkpoint.id
                value  = str(checkpoint.value or '')
                name   = POINTS[checkpoint.subtype].name
                active = checkpoint.active
                self.write_message("::checkpointRegistered#" + str(i) + "#" + name + "#" + value + "#" + str(active))

        # Abschnitt zurücksetzen
        elif command == "resetSector":
            currentPos = self.getGPS();
            if currentPos is not None:
                # Abschnitt beenden
                SECTOR.endSector(currentPos.lon, currentPos.lat)
                # Abschnitt starten
                SECTOR = SECTOR.startSector(STAGE, currentPos.lon, currentPos.lat)
                messageToAllClients(self.wsClients, "Abschnittszähler zurückgesetzt!:success:sectorReset")
#             if DEBUG: prettyprint(RALLYE)
            
        # Abschnittsvorgabe setzen
        elif command == "setSectorLength":
            SECTOR.preset = float(param)
            if float(param) > 0.0:
                messageToAllClients(self.wsClients, "Abschnitt auf "+locale.format_string("%.2f", SECTOR.preset)+" km gesetzt!:success:sectorLengthset")
            else:
                messageToAllClients(self.wsClients, "Vorgabe zurückgesetzt:success:sectorLengthreset")

    # Gleichmäßigkeitsprüfung
        elif command == "startRegtest":
            paramsplit     = param.split("&")
            COUNTDOWN      = int(paramsplit[0])
            SECTOR.preset  = float(paramsplit[1])
            AVG_KMH_PRESET = float(paramsplit[2])
            startRegtest(self)
            messageToAllClients(self.wsClients, "GLP gestartet:success:regTestStarted")
        elif command == "stopRegtest":
            COUNTDOWN      = 0
            AVG_KMH_PRESET = 0.0
            messageToAllClients(self.wsClients, "countdown:0")
            messageToAllClients(self.wsClients, "GLP gestoppt:success:regTestStopped")

    # Settings
        # Neue Rallye starten
        elif command == "newRallye":
            startRallye(False)

        # KMZ Dateien erstellen und herunterladen oder löschen
        elif command == "getFiles":
            if (not saveKMZ(RALLYE)):
                messageToAllClients(self.wsClients, "Neue KMZ Datei konnte nicht erstellt werden:error")
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

        # Buttons definieren
        elif (command.startswith("button")):
            button        = command
            buttonNo      = button.replace("button-", "")
            pointCategory = param
            pointType     = messagesplit[2]
            # In ini abspeichern
            config.set("Settings", button, pointCategory+":"+pointType)
            with open(configFileName, "w") as configfile:
                config.write(configfile)
            messageToAllClients(self.wsClients, "Button " + buttonNo + " als '" + POINTS[pointType].name + "' definiert:success:setButtons#" + button + "#" + POINTS[pointType].icon + "#" + POINTS[pointType].iconcolor + "#" + pointCategory + "#" + pointType)

        # Tripmaster
        elif command == "startDebug":
            messageToAllClients(self.wsClients, "Starte Tornado im DEBUG-Modus neu...")
            stopTornado()
            time.sleep(3)
            subprocess.Popen("start_tripmaster_debug.sh", shell=True)
            sys.exit()
        elif command == "startNew":
            messageToAllClients(self.wsClients, "Starte Tornado neu...")
            stopTornado()
            time.sleep(3)
            subprocess.Popen("sudo /etc/rc.local", shell=True)
            sys.exit()

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

        # Raspberry Pi anhalten oder neu starten
        elif command == "sudoHalt":
            messageToAllClients(self.wsClients, "Fahre RasPi herunter...")
            stopTornado()
            time.sleep(3)
            subprocess.call("sudo shutdown -h now", shell=True)
        elif command == "sudoReboot":
            messageToAllClients(self.wsClients, "Starte RasPi neu...")
            stopTornado()
            time.sleep(3)
            subprocess.call("sudo reboot", shell=True)

        # Nachricht an alle Clients senden
        elif (command == "WarningToAll"):
            messageToAllClients(self.wsClients, param + ":warning")
        elif (command == "ErrorToAll"):
            messageToAllClients(self.wsClients, param + ":error")

        else:
            self.write_message("Unbekannter Befehl - " + command + ":error")

    def getGPS(self):
        # Aktuelle Position
        GPS_CURRENT = getGPSCurrent()
        # Mindestens ein 2D Fix
        if GPS_CURRENT.mode >= 2:
            return GPS_CURRENT
        else:
            messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")
            return None

    # Client getrennt
    def on_close(self):
        # Aus der Liste laufender Clients entfernen
        self.wsClients.remove(self)
        # Wenn kein Client mehr verbunden, dann blinkt die grüne LED
        if len(self.wsClients) == 0:
            LED_GREEN.blink()

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
            # sector_reverse = max(SECTOR.reverse, 0),
        )

class SettingsHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        if SECTOR.reverse == 1:
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

def startTornado():
    global WebServer, WebsocketServer

    logger.info("Starte Tripmaster V3.0")
    logger.info("DEBUG: " + str(DEBUG))
    logger.debug("Tornado-Version: " + tornado.version)

    AsyncIOMainLoop().install()
    
    # WebServer
    WebServer = tornado.httpserver.HTTPServer(Web_Application(), ssl_options={
        "certfile": tripmasterPath+"/certs/servercert.pem",
        "keyfile": tripmasterPath+"/certs/serverkey.pem",
    })
    WebServer.listen(443)
    WebServer.start()
    logger.debug("WebServer gestartet")

    # WebsocketServer
    websocketapp = tornado.web.Application([(r"/(.*)", WebSocketHandler),])
    WebsocketServer = tornado.httpserver.HTTPServer(websocketapp, ssl_options={
        "certfile": tripmasterPath+"/certs/servercert.pem",
        "keyfile": tripmasterPath+"/certs/serverkey.pem",
    })
    WebsocketServer.listen(WebsocketPort)
    WebsocketServer.start()
    logger.debug("WebsocketServer gestartet")

    # Tornado starten
    logger.debug("Starte Tornado")
#     tornado.ioloop.IOLoop.current().start()
    asyncio.get_event_loop().run_forever()

def stopTornado():

    # # UMIN_READER stoppen
    # UMIN_READER_1.cancel()
    # UMIN_READER_2.cancel()
    # # Verbindung mit pigpio beenden
    # pi.stop()

    # # Laufende Etappe beenden
    # if STAGE.isStarted():
        # STAGE.start = 0
        # currentPos = getGPS();
        # if currentPos is not None:
            # STAGE.endStage(currentPos.lon, currentPos.lat)

    WebsocketServer.stop()
    logger.debug("WebServer gestoppt")
    WebServer.stop()
    logger.debug("WebsocketServer gestoppt")

    logger.debug("Beende Tornado")
    asyncio.get_event_loop().stop()
#     tornado.ioloop.IOLoop.current().stop()

    # Grüne LED ausschalten
    LED_GREEN.off()
    # Rote LED schließen und damit freigeben
    LED_RED.close()
    # Rote LED über die Shell einschalten, damit sie auch nach der Beendigung des Tripmasters leuchtet
    # Nach mehrfachem Start/Stop gibt es u.U. den Pfad schon, doppelte Ausführung wirft Fehlermeldung
    if not os.path.exists('/sys/class/gpio/gpio26'):
        subprocess.call("echo 26 > /sys/class/gpio/export", shell=True)
    subprocess.call('echo "out" > /sys/class/gpio/gpio26/direction', shell=True)
    subprocess.call("echo 1 > /sys/class/gpio/gpio26/value", shell=True)


if __name__ == "__main__":
    try:
        # If you want Tornado to leave the logging configuration alone so you can manage it yourself
        options.logging = None

        # Ab Tornado-Version 5.0 wird asyncio verwendet
        # asyncio.set_event_loop(asyncio.new_event_loop())

        startTornado()

    except (KeyboardInterrupt, SystemExit):
        stopTornado()
