#!/usr/bin/env python3

from __future__ import print_function
from datetime import datetime
from gpiozero import DigitalInputDevice, LED
from read_RPM import reader
from tornado.options import options
from tornado.platform.asyncio import AsyncIOMainLoop
from tripmaster_system import DEBUG, SYSTEM, tripmasterPath
from tripmaster_classes import POI, SECTION, loadRallye, saveKMZ, prettyprint
import asyncio
import configparser
import glob
import locale
import logging
import math
import os.path
import pigpio
import subprocess
import sys
import threading
import time
import tornado.web
import tornado.websocket
import tornado.httpserver
# import tornado.ioloop

#-------------------------------------------------------------------
### --- Konfiguration Logger ---
logger = logging.getLogger('Tripmaster')

### --- Systemressourcen ---
### --- Konfiguration Tornado ---
WebServer = None
WebsocketServer = None
WebsocketPort = 7070

### --- Konfiguration Tripmaster ---
# Status Initialisierung
isInitialized = False

### Konfiguration Antriebswellensensor(en)
# GPIO Pins der Sensoren
GPIO_PIN_1 = 17 # weiß
GPIO_PIN_2 = 18 # blau

# DigitalInputDevice setzt standardmäßig pull_up=False, d.h. is_active ist True, wenn Pin ist HIGH
# Reedsensor 1 an Pin 17 (weiß)
REED1 = DigitalInputDevice(GPIO_PIN_1, pull_up=True)
# Reedsensor 2 an Pin 18 (blau)
REED2 = DigitalInputDevice(GPIO_PIN_2, pull_up=True)

# Verbindung zu pigpio Deamon
pi = None
# Die UMIN_READER
UMIN_READER_1 = None
UMIN_READER_2 = None
# Impulse pro Umdrehung
PULSES_PER_REV = 1.0

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

# Liest die Parameter der aktiven Konfiguration und setzt die globalen Variablen
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
# Hat Antriebswellensensor?
HAS_SENSORS = False
# GLP: Vorgabe der Durchschnittsgeschwindigkeit
KMH_AVG_PRESET = 0.0
# GLP: Vorgabe derZeit
COUNTDOWN = 0

# Fortlaufender Index
INDEX = 0

# Rallye
RALLYE = None

# Etappe
STAGE  = None

# Abschnitt
SECTOR = None

# ----------------------------------------------------------------

def startRallye(loadSavedData = True):
    global INDEX, RALLYE, STAGE, SECTOR
    # Daten laden sofern vorhanden    
    if loadSavedData == True:
        RALLYE = loadRallye()
        # Gibt es einen Fehler beim Laden, dann gleich neu machen
        if RALLYE == None:
            loadSavedData = False
        else:
            STAGE  = RALLYE.getLastSubsection()
            SECTOR = STAGE.getLastSubsection()
            # if DEBUG:
                # prettyprint(RALLYE)

    if loadSavedData == False:
        INDEX  = 0
        RALLYE = SECTION(None)
        STAGE  = SECTION(RALLYE)
        SECTOR = SECTION(STAGE)
        RALLYE.startRallye()


# Start der Rallye
startRallye()

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

def getData():
    global HAS_SENSORS, INDEX, RALLYE, STAGE, SECTOR

    # Ein 0 V Potential an einem der beiden Reedsensoren aktiviert die Antriebswellensensoren
    if (REED1.is_active or REED2.is_active) and not HAS_SENSORS:
        HAS_SENSORS = True
        logger.info("Antriebswellensensor(en) automatisch aktiviert!")

    # Index hochzählen
    INDEX  += 1

    # Ermittle Systemstatus und GPS Position
    SYSTEM.setState()

    # Umdrehungen der Antriebswelle(n) pro Minute
    UMIN    = 0.0

    # Geschwindigkeit in Kilometer pro Stunde
    KMH     = 0.0
    kmh_avg = 0.0
    KMH_GPS = 0.0

    # Gefahrene Distanz in km (berechnet aus Geokoordinaten)
    DIST = 0.0

    # noch zurückzulegende Strecke im Abschnitt
    SECTOR_PRESET_REST = 0.0
    # % zurückgelegte Strecke im Abschnitt
    FRAC_SECTOR_DRIVEN = 0
    # Abweichung der durchschnitlichen Geschwindigkeit von der Vorgabe
    dev_kmh_avg        = 0.0

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
            STAGE = STAGE.startStage(RALLYE, SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
            # Abschnitt starten
            SECTOR = SECTOR.startSector(STAGE, SYSTEM.GPS_LON, SYSTEM.GPS_LAT)

        # Mindestens ein 2D Fix
        if (SYSTEM.GPS_MODE >= 2):

            # KMH_GPS = GPS_CURRENT.speed() * 3.6 - gibt auf einmal nur noch 0.0 zurück
            if (SYSTEM.GPS_HSPEED > 1.0):
                KMH_GPS = SYSTEM.GPS_HSPEED * 3.6

            if (SECTOR.getLon() is not None) and (SECTOR.getLat() is not None) and (KMH_GPS > 0.0):
                DIST = calcGPSdistance(SECTOR.getLon(), SYSTEM.GPS_LON, SECTOR.getLat(), SYSTEM.GPS_LAT)

            KMH            = KMH_GPS
            RALLYE.km     += DIST
            RALLYE.km_gps  = RALLYE.km
            STAGE.km      += DIST * SECTOR.reverse
            STAGE.km_gps   = STAGE.km
            SECTOR.km     += DIST * SECTOR.reverse
            SECTOR.km_gps  = SECTOR.km
            SECTOR.setPoint(SYSTEM.GPS_LON, SYSTEM.GPS_LAT, "sector", "track")

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
        # noch zurückzulegende Strecke im Abschnitt
        SECTOR_PRESET_REST = max(SECTOR.preset - SECTOR.km, 0)

        if SECTOR.t > 0.0:
            # Durchschnittliche Geschwindigkeit in Kilometer pro Stunde im Abschnitt
            kmh_avg = SECTOR.km * 1000 / SECTOR.t * 3.6
            if KMH_AVG_PRESET > 0.0:
                dev_kmh_avg = kmh_avg - KMH_AVG_PRESET

        if STAGE.getDuration() > 0:
            STAGE_TIMETOFINISH = STAGE.finish - int(datetime.timestamp(datetime.now()))
            STAGE_FRACTIME     = round((1 - STAGE_TIMETOFINISH / STAGE.getDuration()) * 100)
    else:
        if STAGE.start > 0:
            STAGE_TIMETOSTART = STAGE.start - int(datetime.timestamp(datetime.now()))

    # Aktuelle Zeit als String HH-MM-SS
    NOW = datetime.now().strftime('%H-%M-%S') # .%f')[:-3]
    # NOW2 = datetime.now().strftime('%H-%M-%S.%f')[:-3]
    
    datastring = "data:{0:}:{1:0.1f}:{2:0.6f}:{3:0.6f}:{4:}:{5:}:{6:}:{7:}:{8:}:{9:}:{10:0.2f}:{11:0.2f}:{12:0.2f}:{13:}:{14:0.2f}:{15:0.2f}:{16:0.1f}:{17:0.1f}:{18:}:{19:0.2f}:{20:}:{21:0.1f}:{22:0.1f}:{23:}".format(
        NOW, KMH, SYSTEM.GPS_LON, SYSTEM.GPS_LAT, 
        int(HAS_SENSORS), int(SYSTEM.CLOCK_SYNCED), int(STAGE.isStarted()), 
        int(STAGE_FRACTIME), STAGE_TIMETOSTART, STAGE_TIMETOFINISH, 
        SECTOR.km, SECTOR.preset, SECTOR_PRESET_REST, FRAC_SECTOR_DRIVEN, STAGE.km, RALLYE.km, 
        kmh_avg, dev_kmh_avg, 
        SYSTEM.GPS_MODE, SYSTEM.UBAT, SYSTEM.UBAT_CAP, SYSTEM.CPU_TEMP, SYSTEM.CPU_LOAD,
        int(DEBUG))
    
    # logger.info("data:{0:}".format(NOW2))

    return datastring

def calcGPSdistance(lambda1, lambda2, phi1, phi2):
    l1 = math.radians(lambda1)
    l2 = math.radians(lambda2)
    p1 = math.radians(phi1)
    p2 = math.radians(phi2)
    x  = (l2-l1) * math.cos((p1+p2)/2)
    y  = (p2-p1)
    return math.sqrt(x*x + y*y) * 6371

def pushRallyeData(clients, what, when):
    if (SYSTEM.UBAT_CAP < -3):
        messageToAllClients(clients, "Akku leer! Fahre RasPi herunter...")
        stopTornado()
        time.sleep(3)
        subprocess.call("sudo shutdown -h now", shell=True)
    else:
        what    = str(what)
        message = WebRequestHandler(what.splitlines());
        messageToAllClients(clients, message)
        
        # jetzt
        now     = datetime.now()
        # Differenz zwischen Jetzt und Idealzeit
        diff    = now - now.replace(microsecond=0)
        # Zeit bis zum nächsten Lauf
        when    = SAMPLE_TIME - diff.total_seconds()
        
        # logger.debug(now.strftime('%H-%M-%S.%f')[:-3] + "\twhen\t{0:0.6f}\tdiff\t{1:0.3f}".format(when, diff.total_seconds()))
        
        timed   = threading.Timer( when, pushRallyeData, [clients, what, when] )
        timed.daemon = True
        timed.start()

def startRegtest(client):
    timed        = threading.Timer(1.0, pushRegtestData, [client.wsClients, "regTest", "1.0"] )
    timed.daemon = True
    timed.start()

def pushRegtestData(clients, what, when):
    global KMH_AVG_PRESET
    what      = str(what)
    when      = float(when)
    message   = WebRequestHandler(what.splitlines())
    countdown = int(message)
    if countdown == 0:
        messageToAllClients(clients, "countdown:"+message)
        KMH_AVG_PRESET = 0.0
        messageToAllClients(clients, "GLP gestoppt:success:regTestStopped")
    elif countdown > 0:
        messageToAllClients(clients, "countdown:"+message)
        timed        = threading.Timer( when, pushRegtestData, [clients, what, when] )
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
        global isInitialized, pi, UMIN_READER_1, UMIN_READER_2, RALLYE, STAGE, SECTOR
        self.stream.set_nodelay(True)
        # Jeder WebSocket Client wird der Liste wsClients hinzugefügt
        self.wsClients.append(self)
        # Die ID ist der Index in der Liste wsClients
        self.id = "Client #" + str(self.wsClients.index(self) + 1) + " (" + page + ")"
        
        # Wenn es der Timer Thread noch nicht gestartet ist, alles initialisieren
        if isInitialized == False:
            # Verbinden mit pigpio
            pi = pigpio.pi()
            # UMIN_READER starten
            UMIN_READER_1 = reader(pi, GPIO_PIN_1, PULSES_PER_REV)
            UMIN_READER_2 = reader(pi, GPIO_PIN_2, PULSES_PER_REV)
            # Timer starten
            timed = threading.Timer(SAMPLE_TIME, pushRallyeData, [self.wsClients, "getData", "{:.1f}".format(SAMPLE_TIME)] )
            timed.daemon = True
            timed.start()
            isInitialized = True
            logger.info("Thread für den Tripmaster gestartet")
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
            self.write_message("::setButtons#" + button + "#" + POI[pointType].icon + "#" + POI[pointType].iconcolor + "#" + pointCategory + "#" + pointType)

        stagestatus = "stage_start"
        if STAGE.start == 0:
            stagestatus = "stage_finish"

        messageToAllClients(self.wsClients, "::setButtons#button-togglestage#" + POI[stagestatus].icon + "#" + POI[stagestatus].iconcolor + "#toggleStage#")

        SYSTEM.setNClients(len(self.wsClients))
        logger.info("Websocket geöffnet - Clients: " + str(len(self.wsClients)))

    # the client sent a message
    def on_message(self, message):
        global ACTIVE_CONFIG, COUNTDOWN, KMH_AVG_PRESET, RALLYE, STAGE, SECTOR
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
            if self.isGPSexact():
                if (STAGE.start == 0):
                    # Etappe starten
                    STAGE = STAGE.startStage(RALLYE, SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
                    # Abschnitt starten
                    SECTOR = SECTOR.startSector(STAGE, SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
                    messageToAllClients(self.wsClients, "Etappe gestartet:success:setButtons#button-togglestage#" + POI["stage_start"].icon + "#" + POI["stage_start"].iconcolor)
                else:
                    # Abschnitt beenden
                    SECTOR.endSector(SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
                    # Etappe beenden
                    STAGE.endStage(RALLYE, SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
                    messageToAllClients(self.wsClients, "Etappe beendet:success:setButtons#button-togglestage#" + POI["stage_finish"].icon + "#" + POI["stage_finish"].iconcolor)
            # prettyprint(RALLYE)
            
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
                messageToAllClients(self.wsClients, "Etappenstartzeit gelöscht:success:setButtons#button-togglestage#" + POI["stage_finish"].icon + "#" + POI["stage_finish"].iconcolor)
                messageToAllClients(self.wsClients, "::switchToMain")
            else:
                STAGE.setAutostart(True, int(int(param) / 1000))
                starttime = datetime.fromtimestamp(STAGE.start).strftime("%H&#058;%M")
                messageToAllClients(self.wsClients, "Etappe startet automatisch um " + starttime + " Uhr:success:setButtons#button-togglestage#" + POI["stage_start"].icon + "#" + POI["stage_start"].iconcolor)
                messageToAllClients(self.wsClients, "::switchToClock")

        # Punkte registrieren
        elif (command == "countpoint") or (command == "checkpoint"):
            if self.isGPSexact():
                ptype    = command
                subptype = param
                i        = STAGE.setPoint(SYSTEM.GPS_LON, SYSTEM.GPS_LAT, ptype, subptype)
                messageToAllClients(self.wsClients, POI[subptype].name + " registriert:success:" + ptype + "Registered#" + str(i) + "#" + POI[subptype].name + "##1")

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
                #                             or '') konvertiert None in ''
                value  = str(countpoint.value or '')
                name   = POI[countpoint.poisubtype].name
                active = countpoint.active
                self.write_message("::countpointRegistered#" + str(i) + "#" + name + "#" + value + "#" + str(active))
            for checkpoint in STAGE.checkpoints:
                i      = checkpoint.id
                value  = str(checkpoint.value or '')
                name   = POI[checkpoint.poisubtype].name
                active = checkpoint.active
                self.write_message("::checkpointRegistered#" + str(i) + "#" + name + "#" + value + "#" + str(active))

        # Abschnitt zurücksetzen
        elif command == "resetSector":
            if self.isGPSexact():
                # Abschnitt beenden
                SECTOR.endSector(SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
                # Abschnitt starten
                SECTOR = SECTOR.startSector(STAGE, SYSTEM.GPS_LON, SYSTEM.GPS_LAT)
                messageToAllClients(self.wsClients, "Abschnittszähler zurückgesetzt!:success:sectorReset")
            # prettyprint(RALLYE)
            
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
            KMH_AVG_PRESET = float(paramsplit[2])
            startRegtest(self)
            messageToAllClients(self.wsClients, "GLP gestartet:success:regTestStarted")
        elif command == "stopRegtest":
            COUNTDOWN      = 0
            KMH_AVG_PRESET = 0.0
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
            messageToAllClients(self.wsClients, "Button " + buttonNo + " als '" + POI[pointType].name + "' definiert:success:setButtons#" + button + "#" + POI[pointType].icon + "#" + POI[pointType].iconcolor + "#" + pointCategory + "#" + pointType)

        # Tripmaster
        elif command == "startDebug":
            messageToAllClients(self.wsClients, "Starte Tripmaster im DEBUG-Modus neu...")
            time.sleep(3)
            subprocess.Popen(tripmasterPath + "/script/start_tripmaster_debug.sh", shell=True)
            sys.exit()
        elif command == "startNew":
            messageToAllClients(self.wsClients, "Starte Tripmaster neu...")
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

    def isGPSexact(self):
        # Check ob das GPS mindestens einen 2D Fix liefert
        if not SYSTEM.GPS_GOODFIX:
            messageToAllClients(self.wsClients, "GPS ungenau! Wiederholen:error")
        return SYSTEM.GPS_GOODFIX

    # Client getrennt
    def on_close(self):
        # Aus der Liste laufender Clients entfernen
        self.wsClients.remove(self)
        n_clients = len(self.wsClients)
        SYSTEM.setNClients(n_clients)
        if n_clients == 0:            
            logger.info("Alle Websockets geschlossen")
        else:
            logger.info("Websocket geschlossen - Clients: " + str(n_clients))


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
            autoreload = True,
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

    logger.debug("Starte Tornado V" + tornado.version)

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

    # Den Event Loop starten, damit Tornado dauerhaft auf Events von den obigen Sockets hört
    logger.debug("Starte Event Loop")
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
        # if isGPSexact():
            # STAGE.endStage(SYSTEM.GPS_LON, SYSTEM.GPS_LAT)

    WebsocketServer.stop()
    logger.debug("WebsocketServer gestoppt")
    WebServer.stop()
    logger.debug("WebServer gestoppt")

    asyncio.get_event_loop().stop()
    logger.debug("Event Loop gestoppt")
#     tornado.ioloop.IOLoop.current().stop()

    # Der GPS-Thread muss die Kontrolle über die LEDs an __main__ abgeben...
    SYSTEM.releaseLEDs()
    # ... und __main__ mus die LED-Objekte schließen, sonst funktionieren die shell-Aufrufe nicht
    LED(19, initial_value=False).close()
    LED(26, initial_value=True).close()
    # Grüne LED über die Shell ausschalten
    # Nach mehrfachem Start/Stop gibt es u.U. den Pfad schon, doppelte Ausführung wirft Fehlermeldung
    if not os.path.exists('/sys/class/gpio/gpio19'):
        subprocess.call("echo 19 > /sys/class/gpio/export", shell=True)
    subprocess.call('echo "out" > /sys/class/gpio/gpio19/direction', shell=True)
    subprocess.call("echo 0 > /sys/class/gpio/gpio19/value", shell=True)
    # Rote LED über die Shell einschalten, damit sie auch nach der Beendigung des Tripmasters leuchtet
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
