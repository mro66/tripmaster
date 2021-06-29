#!/usr/bin/env python3

from datetime import datetime
from tripmaster_system import trackFile, rallyeFile, tripmasterPath
import copy
import csv
import locale
import logging
import os
import pickle
import simplekml
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

    def startRallye(self):
        current_date = "{0:%Y%m%d_%H%M}".format(datetime.now())
        if os.path.exists(rallyeFile):
            os.rename(rallyeFile, tripmasterPath+"/out/"+current_date+".dat")
        if os.path.exists(trackFile):
            os.rename(trackFile, tripmasterPath+"/out/"+current_date+".csv")
        # legt leere Rallyedatei an
        self.saveRallye()
        # legt leere TrackCSV an
        open(trackFile, 'a').close()
        
    
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
        
        self.saveRallye()
        return newPoint.id

    def changePoint(self, ptype, i, active, value):
        if ptype == "countpoint":
            self.countpoints[i].active = active
        elif ptype == "checkpoint":
            self.checkpoints[i].active = active
            self.checkpoints[i].value = value
        self.saveRallye()
        

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

    def saveRallye(self):
        with open(rallyeFile, 'wb') as fp:
            pickle.dump(self.root, fp)

            
def loadRallye():
    if os.path.exists(rallyeFile) and (os.path.getsize(rallyeFile) > 0):
        try:
            with open(rallyeFile, 'rb') as fp:
                return pickle.load(fp)
        except EOFError:
            logger.error("EOFError!")
    return None

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
            subtypes.add(p.poisubtype)
        # Zählpunkte
        for p in stage.countpoints:
            subtypes.add(p.poisubtype)
        # Orientierungskontrollen
        for p in stage.checkpoints:
            subtypes.add(p.poisubtype)

    # Nur die Styles für die genutzten POINT subtypes definieren
    styles = {};
    for s in subtypes:
        icon = tripmasterPath + "/static/kmz/" + s + ".gif"
        styles[s] = simplekml.Style()
        styles[s].iconstyle.icon.href = KML.addfile(icon)

    # Styles für Tracks
    styles["track0"]                 = simplekml.Style()
    styles["track0"].linestyle.width = 5
    styles["track0"].linestyle.color = "ff4f53d9"  # rot
    styles["track1"]                 = simplekml.Style()
    styles["track1"].linestyle.width = 5
    styles["track1"].linestyle.color = "ff5cb85c"  # grün

    logger.debug("KML Vorbereitung --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()

    # Eine deepcopy des RALLYE Objektes erstellen, da die POINTS der Abschnitte zum Ausgeben überschrieben werden
    r = copy.deepcopy(rallye)

    logger.debug("deepcopy des RALLYE Objektes erstellen --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()

    # Inhalt der TrackCSV in eine Liste kopieren
    with open(trackFile) as csv_file:
        tracks = list(csv.reader(csv_file))
        
    logger.debug("Inhalt der TrackCSV in eine Liste kopieren --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    # Gespeicherte POINTS in den Abschnitten löschen
    for stage in r.subsection:
        for sector in stage.subsection:
            sector.points.clear()    

    # Überschreiben der POINTS in den Abschnitten mit dem Inhalt der TrackCSV
    for row in tracks:
        stage_id  = int(row[0])
        sector_id = int(row[1])
        lon       = float(row[2])
        lat       = float(row[3])
        for stage in r.subsection:
            for sector in stage.subsection:
                if (stage.id == stage_id) and (sector.id == sector_id):
                    newPoint = POINT(lon, lat, "sector", "track")
                    sector.points.append(newPoint)

    logger.debug("Überschreiben der POINTS in den Abschnitten mit dem Inhalt der TrackCSV --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    for stage in r.subsection:

        # Ausgabe der Etappen
        sf = KML.newfolder(name="Etappe " + str(stage.id+1))
        for p in stage.points:
            # 'name' ist der label, 'description' erscheint darunter
            newpoint = sf.newpoint(coords = [(p.lon, p.lat)], \
                                   name = POI[p.poisubtype].name, \
                                   description = "Länge: " + locale.format_string("%.2f", stage.km) + " km\n" + \
                                                 "Start: " + datetime.fromtimestamp(stage.dtstart).strftime("%d.%m.%Y %H:%M") + "\n" + \
                                                 "Ziel: " + datetime.fromtimestamp(stage.dtfinish).strftime("%d.%m.%Y %H:%M") + "\n" + \
                                                 "Dauer: " + time.strftime('%H:%M', stage.duration) + " h")
            newpoint.style = styles[p.poisubtype]

        # Ausgabe der Abschnitte mit Zählpunkten und Orientierungskontrollen
        f = sf.newfolder(name="Abschnitte")
        for sector in stage.subsection:
            newtrack = f.newlinestring(name = "Abschnitt "+str(sector.id+1), \
                                       description = "Länge: " + locale.format_string("%.2f", sector.km) + " km\n" + \
                                                     "Start: " + datetime.fromtimestamp(sector.dtstart).strftime("%d.%m.%Y %H:%M") + "\n" + \
                                                     "Ziel: " + datetime.fromtimestamp(sector.dtfinish).strftime("%d.%m.%Y %H:%M") + "\n" + \
                                                     "Dauer: " + time.strftime('%H:%M', sector.duration) + " h")
            newtrack.style = styles["track"+str(sector.id % 2)]
            for p in sector.points:
                newtrack.coords.addcoordinates([(p.lon, p.lat)])

        if len(stage.countpoints) > 0:
            f = sf.newfolder(name="Zählpunkte")
            # Nur aktive Punkte werden gespeichert
            for p in (x for x in stage.countpoints if x.active == 1):
                newpoint = f.newpoint(coords = [(p.lon, p.lat)], \
                                      description = POI[p.poisubtype].name)
                newpoint.style = styles[p.poisubtype]

        if len(stage.checkpoints) > 0:
            f = sf.newfolder(name="Orientierungskontrollen")
            for p in (x for x in stage.checkpoints if x.active == 1):
                newpoint = f.newpoint(coords = [(p.lon, p.lat)], \
                                      name = p.value, \
                                      description = POI[p.poisubtype].name)
                newpoint.style = styles[p.poisubtype]

    logger.debug("KML erstellen --- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
    
    KML_FILE = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.kmz".format(datetime.now())
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
    print('\n------ prettyprint(rallye) ---------------')
    
    # eine deepcopy des RALLYE Objektes erstellen, da die POINTS der Abschnitte zum Ausgeben überschrieben werden
    r = copy.deepcopy(rallye)

    # Inhalt der TrackCSV in eine Liste kopieren
    with open(trackFile) as csv_file:
        tracks = list(csv.reader(csv_file))
        
    # Gespeicherte POINTS in den Abschnitten löschen
    for stage in r.subsection:
        for sector in stage.subsection:
            sector.points.clear()    
    
    # Überschreiben der POINTS in den Abschnitten mit dem Inhalt der TrackCSV
    for row in tracks:
        stage_id  = int(row[0])
        sector_id = int(row[1])
        lon       = float(row[2])
        lat       = float(row[3])
        for stage in r.subsection:
            for sector in stage.subsection:
                if (stage.id == stage_id) and (sector.id == sector_id):
                    newPoint = POINT(lon, lat, "sector", "track")
                    sector.points.append(newPoint)

    # Ausgabe der Rallye
    if (r.dtstart != None) and (r.dtfinish != None):
        print("\nRallye")
        print("  Start:  " + datetime.fromtimestamp(r.dtstart).strftime("%d.%m.%Y %H:%M"))
        print("   Ziel:  " + datetime.fromtimestamp(r.dtfinish).strftime("%d.%m.%Y %H:%M"))
        print("  Dauer:  " + time.strftime('%H:%M', r.duration) + " h")
        print("  Länge:  {:0.2f}".format(r.km) +" km")
    
        # Ausgabe der Etappen
        for stage in r.subsection:
    
            print("\n  Etappe " + str(stage.id+1))
            print("    Start:  " + datetime.fromtimestamp(stage.dtstart).strftime("%d.%m.%Y %H:%M"))
            print("     Ziel:  " + datetime.fromtimestamp(stage.dtfinish).strftime("%d.%m.%Y %H:%M"))
            print("    Dauer:  " + time.strftime('%H:%M', stage.duration) + " h")
            print("    Länge:  {:0.2f}".format(stage.km) +" km")
            for p in stage.points:
                print("            " + POI[p.poisubtype].name)
                print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))
    
            # Ausgabe der Abschnitte mit Zählpunkten und Orientierungskontrollen
            for sector in stage.subsection:
                print("\n    Abschnitt " + str(sector.id+1))
                print("      Start:  " + datetime.fromtimestamp(sector.dtstart).strftime("%d.%m.%Y %H:%M"))
                print("       Ziel:  " + datetime.fromtimestamp(sector.dtfinish).strftime("%d.%m.%Y %H:%M"))
                print("      Dauer:  " + time.strftime('%H:%M', sector.duration) + " h")
                print("      Länge:  {:0.2f}".format(sector.km) +" km")
                # Ausgabe aller Trackpoints im Abschnitt - kann lang werden
                # for p in sector.points:
                    # print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))
     
            if len(stage.countpoints) > 0:
                print("  Zählpunkte")
                for p in (x for x in stage.countpoints if x.active == 1):
                    print("    name:   " + POI[p.poisubtype].name)
                    print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))
     
            if len(stage.checkpoints) > 0:
                print("  Orientierungskontrollen")
                for p in (x for x in stage.checkpoints if x.active == 1):
                    print("    name:   " + POI[p.poisubtype].name)
                    if p.value == None:
                        value = "-"
                    else:
                        value = p.value
                    print("    value:  " + value)
                    print("    coords: {0:0.4f}, {1:0.4f}".format(p.lon, p.lat))
