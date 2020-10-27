from datetime import datetime

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
    "null"        : POINT_ATTR("Keine", "fas fa-question", "red"),
     }

class POINT:
    def __init__(self, lon, lat, type = None, subtype = None):
        self.id     = None
        self.lon    = lon
        self.lat    = lat
        self.value  = None       # z. B. Buchstabe von Ortsschildern
        self.active = 1
        if (type != None):
            self.type    = type
            self.subtype = subtype
        else:
            self.type = "track"

# Rallye, Etappe und Abschnitt sind SECTIONs
class SECTION:
    # global REVERSE
    def __init__(self):
        self.id          = None     # Index, bei subsections die Position in der Liste
        self.t           = 0.0      # Messpunkt
        self.autostart   = False    # Startzeit einer Etappe ist eingerichtet
        self.start       = 0        # Startzeit
        self.finish      = 0        # Zielzeit
        self.preset      = 0.0      # Streckenvorgabe
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
        isStarted = (self.start > 0) and (self.start < datetime.timestamp(datetime.now()))
        return isStarted
        
    def setAutostart(self, autostart, start):
        self.autostart = autostart
        self.start     = start

    def startStage(self, rallye, lon, lat):
        newStage       = SECTION()
        newStage.start = datetime.timestamp(datetime.now())
        newStage.km    = 0.0
        rallye.subsection.append(newStage)
        newStage.id    = rallye.subsection.index(newStage)
        # logger.debug("   Etappe " + str(newStage.id) + " gestartet: " + locale.format("%.2f", lon) + "/" + locale.format("%.2f", lat))
        newStage.setPoint(lon, lat, "stage", "stage_start")
        return newStage

    def endStage(self, lon, lat):
        self.start = 0
        self.setPoint(lon, lat, "stage", "stage_finish")
        # logger.debug("   Etappe " + str(self.id) + " gestoppt:  " + locale.format("%.2f", lon) + "/" + locale.format("%.2f", lat))       

    def startSector(self, stage, lon, lat):
        newSector = SECTION()
        # Neue Abschnitte fahren immer vorwärts
        # REVERSE = +1
        stage.subsection.append(newSector)
        newSector.id = stage.subsection.index(newSector)
        newSector.setPoint(lon, lat)
        # logger.debug("Abschnitt " + str(newSector.id) + " gestartet: " + locale.format("%.2f", lon) + "/" + locale.format("%.2f", lat))
        return newSector

    def endSector(self, lon, lat):
        self.setPoint(lon, lat)
        # logger.debug("Abschnitt " + str(self.id) + " gestoppt:  " + locale.format("%.2f", lon) + "/" + locale.format("%.2f", lat))

    def setPoint(self, lon, lat, type = None, subtype = None):
        # Bounding Box von Deutschland: (5.98865807458, 47.3024876979, 15.0169958839, 54.983104153)),
        if (15.1 > lon > 5.9) and (55.0 > lat > 47.3):
            newPoint = POINT(lon, lat, type, subtype)
            if (type == 'countpoint'):
                self.countpoints.append(newPoint)
                newPoint.id = self.countpoints.index(newPoint)
            elif (type == 'checkpoint'):
                self.checkpoints.append(newPoint)
                newPoint.id = self.checkpoints.index(newPoint)
            else:
                self.points.append(newPoint)
                newPoint.id = self.points.index(newPoint)
                # if DEBUG and (type is None):
                    # logger.debug("Trackpunkt " + str(newPoint.id) + ": " + locale.format("%.4f", lon) + "/" + locale.format("%.4f", lat))
            pickleData()
            return newPoint.id

    def changePoint(self, type, id, active, value):
        if type == "countpoint":
            self.countpoints[id].active = active
        elif type == "checkpoint":
            self.checkpoints[id].active = active
            self.checkpoints[id].value = value
        pickleData()

    # Nur für Abschnitt/SECTOR: Holt Koordinate des letzten Listeneintrags
    def getLon(self):
        if len(self.points) > 0:
            return self.points[-1].lon
        else:
            None
    def getLat(self):
        if len(self.points) > 0:
            return self.points[-1].lat
        else:
            None
    
    # Gibt beim Daten laden die letzte subsection zurück
    def getLastSubsection(self):
        if (len(self.subsection) > 0):
            return self.subsection[-1]
        else:
            return SECTION()
