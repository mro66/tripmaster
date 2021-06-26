#!/usr/bin/env python3

from datetime import datetime
from tripmaster_system import trackFile, rallyeFile
import csv
import locale
import logging
import pickle
import time

logger = logging.getLogger('Tripmaster')

# Komma als Dezimaltrennzeichen
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

class POI_ATTR:
    def __init__(self, name, icon, iconcolor):
        self.name = name
        self.icon = icon
        self.iconcolor = "var(--tm-" + iconcolor + ")"

# POI sind vom Typ Dictionary: Der KEY ist der subtype, die VALUES vom Typ List mit name, icon, iconcolor
POI = {
    # Etappenstart und -ziel
    "stage_start" : POI_ATTR("Start Etappe", "fas fa-flag-checkered", "red"),
    "stage_finish": POI_ATTR("Ende Etappe", "fas fa-flag-checkered", "green"),
    # Zählpunkte und Orientierungskontrollen
    "roundabout"  : POI_ATTR("Kreisverkehr", "fas fa-sync", "blue"),
    "townsign"    : POI_ATTR("Ortsschild", "fas fa-sign", "yellow"),
    "stampcheck"  : POI_ATTR("Stempelkontrolle", "fas fa-stamp", "red"),
    "mutecheck"   : POI_ATTR("Stummer Wächter", "fas fa-neuter", "green"),
    "countpoint"  : POI_ATTR("Sonstiges", "fas fa-hashtag", "blue"),
    "checkpoint"  : POI_ATTR("Sonstige OK", "fas fa-map-marker-alt", "green"),
    # Sonstige
    "null"        : POI_ATTR("Inaktiv", "fas fa-question", "lightgray"),
     }

# Der geometrische Punkt mit Geokoordinaten und (optional) einer POI-(Sub)Typisierung
class POINT:
    def __init__(self, lon, lat, poitype = None, poisubtype = None):
        self.id     = None
        self.lon    = lon
        self.lat    = lat
        self.value  = None               # z.B. Buchstabe von Ortsschildern
        self.active = 1
        if (poitype != None):
            self.poitype    = poitype    # z.B. Checkpunkt
            self.poisubtype = poisubtype # z.B. Ortsschild
        else:
            self.type = "track"

# Rallye, Etappe und Abschnitt sind SECTIONs
class SECTION:
    def __init__(self, parent):
        if (parent == None):
            # ... dann wird gerade das Wurzelobjekt initialisiert
            root = self
            pid = -1
        else:
            # ... ansonsten immer das Wurzelobjekt des Elternobjekts 'vererben'
            root = parent.root                
            pid = parent.id
        self.root        = root     # Wurzelobjekt = RALLYE
        self.parent_id   = pid      # ID des Elternobjekts (z.B. in welcher Etappe liegt der Abschnitt)
        self.id          = None     # Index, bei subsections die Position in der Liste
        self.t           = 0.0      # Messpunkt
        self.autostart   = False    # Startzeit einer Etappe ist eingerichtet
        self.start       = 0        # Startzeit (wenn größer 0, dann ist gestartet)
        self.finish      = 0        # Zielzeit
        self.dtstart     = None     # Startzeitpunkt
        self.dtfinish    = None     # Zielzeitpunkt
        self.duration    = None     # Zielzeitpunkt - Startzeitpunkt in Sekunden
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
        newstage         = SECTION(rallye)
        dtnow            = datetime.timestamp(datetime.now())
        newstage.start   = dtnow
        newstage.dtstart = dtnow
        newstage.km      = 0.0
        # Neue Etappe der Rallye zuordnen
        rallye.subsection.append(newstage)
        newstage.id      = rallye.subsection.index(newstage)
        # Wenn die Etappe 0 gestartet wird, wird auch die Rallye gestartet
        if (newstage.id == 0):
            rallye.dtstart = dtnow
            logger.debug("     Rallye gestartet")
        newstage.setPoint(lon, lat, "stage", "stage_start")
        logger.debug("   Etappe " + str(newstage.id) + " gestartet: " + \
                     locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat) + "/" + \
                     datetime.fromtimestamp(dtnow).strftime("%d.%m.%Y %H:%M"))
        return newstage

    def endStage(self, rallye, lon, lat):
        self.start      = 0
        dtnow           = datetime.timestamp(datetime.now())
        self.dtfinish   = dtnow
        self.duration   = time.gmtime(dtnow - self.dtstart)
        # Rallye beenden
        rallye.dtfinish = dtnow
        rallye.duration = time.gmtime(dtnow - rallye.dtstart)
        # Rallye Gesamtlänge = Summe der Etappenlängen
        rallye.km       = 0.0
        for stage in rallye.subsection:
            rallye.km  += stage.km
        self.setPoint(lon, lat, "stage", "stage_finish")
        logger.debug("   Etappe " + str(self.id) + " gestoppt:  " + \
                     locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat) + "/" + \
                     datetime.fromtimestamp(dtnow).strftime("%d.%m.%Y %H:%M"))

    def startSector(self, stage, lon, lat):
        newsector         = SECTION(stage)
        dtnow             = datetime.timestamp(datetime.now())
        newsector.dtstart = dtnow
        # Neuen Abschnitt der Etappe zuordnen
        stage.subsection.append(newsector)
        newsector.id      = stage.subsection.index(newsector)
        newsector.setPoint(lon, lat, "sector", "sector_start")
        logger.debug("Abschnitt " + str(newsector.id) + " gestartet: " + \
                     locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat) + "/" + \
                     datetime.fromtimestamp(dtnow).strftime("%d.%m.%Y %H:%M"))
        return newsector

    def endSector(self, lon, lat):
        dtnow         = datetime.timestamp(datetime.now())
        self.dtfinish = dtnow
        self.duration = time.gmtime(self.dtfinish - self.dtstart)
        self.setPoint(lon, lat, "sector", "sector_finish")
        logger.debug("Abschnitt " + str(self.id) + " gestoppt:  " + \
                     locale.format_string("%.2f", lon) + "/" + locale.format_string("%.2f", lat) + "/" + \
                     datetime.fromtimestamp(dtnow).strftime("%d.%m.%Y %H:%M"))

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
            # logger.debug("Trackpunkt " + str(newPoint.id) + ": " + locale.format_string("%.4f", lon) + "/" + locale.format_string("%.4f", lat))
            # logger.debug("parent.id: {0:}, self.id: {1:}, lon: {2:0.4f}, lat {3:0.4f} ".format(self.parent_id, self.id, lon, lat))
        else:
            logger.error("Unbekannter oder fehlender Punkttyp (ptype)")
        
        self.pickleData()
        return newPoint.id

    def changePoint(self, ptype, i, active, value):
        if ptype == "countpoint":
            self.countpoints[i].active = active
        elif ptype == "checkpoint":
            self.checkpoints[i].active = active
            self.checkpoints[i].value = value
        self.pickleData()
        

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
            return SECTION(self)

    def pickleData(self):
        with open(rallyeFile, 'wb') as fp:
            pickle.dump(self.root, fp)
