#!/usr/bin/env python3

from datetime import datetime
# from tripmaster_web import POINT_ATTR
# from tripmaster_web import POINTS
# from tripmaster_web import POINT
# from tripmaster_web import SECTION
import locale
import os.path
import pickle
import simplekml

# Rallye, Etappe und Abschnitt sind SECTIONs
class SECTION:
    def __init__(self):
        self.id          = None     # Index, bei subsections die Position in der Liste
        self.t           = 0.0      # Messpunkt
        self.autostart   = False    # Startzeit einer Etappe ist eingerichtet
        self.start       = 0        # Startzeit
        self.finish      = 0        # Zielzeit
        self.preset      = 0.0      # Streckenvorgabe
        self.reverse     = 1        # 1 = Tacho läuft normal, -1 = Tacho läuft rückwärts
        self.km          = 0.0      # Strecke
        self.km_gps      = 0.0      # Strecke (GPS)
        self.points      = []       # Start/Ende bei Etappen, Trackpunkte bei Abschnitten
        self.countpoints = []       # Zählpunkte bei Etappen
        self.checkpoints = []       # Orientierungskontrollen bei Etappen
        self.subsection  = []       # Untersektionen (Etappen bei Rallye, Abschnitte bei Etappen)

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
        self.type    = type
        self.subtype = subtype

# Programmpfad für Dateiausgaben
tripmasterPath = os.path.dirname(os.path.abspath(__file__))
# Komma als Dezimaltrennzeichen
locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

# Geodatenausgabe als KML
class saveKMZ:
    def __init__(self):
        pickleFile = tripmasterPath + '/out/pickle.dat' 
        RALLYE = None
        with open(pickleFile, 'rb') as fp:
            RALLYE = pickle.load(fp)
        
        # ------------------------------------------------------------------
        
        self.KML = simplekml.Kml(open=1)
        KML_FILE = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.kmz".format(datetime.now());
        
        # Set aller genutzten POINT subtypes, Sets haben keine(!) Duplikate
        subtypes = set();
        
        # RALLYE und SECTOR haben keine Punkte (SECTOR hat nur Tracks)
        for STAGE in RALLYE.subsection:
            # Etappebeginn, -ende 
            for p in STAGE.points:
                subtypes.add(p.subtype)
            # Zählpunkte
            for p in STAGE.countpoints:
                subtypes.add(p.subtype)
            # Orientierungskontrollen
            for p in STAGE.checkpoints:
                subtypes.add(p.subtype)
            
        # Nur die Styles für die genutzten POINT subtypes definieren
        self.STYLES = {};
        for s in subtypes:
            self.STYLES[s] = self.setPointStyle(s)
        # Styles für Tracks
        self.STYLES["track0"] = simplekml.Style()
        self.STYLES["track0"].linestyle.width = 5
        self.STYLES["track0"].linestyle.color = "ff4f53d9"  # rot
        self.STYLES["track1"] = simplekml.Style()
        self.STYLES["track1"].linestyle.width = 5
        self.STYLES["track1"].linestyle.color = "ff5cb85c"  # grün
            
        for STAGE in RALLYE.subsection:
        
            sf = self.KML.newfolder(name="Etappe " + str(STAGE.id+1))            
            for p in STAGE.points:
                # 'name' ist der label, 'description' erscheint darunter
                newpoint = sf.newpoint(coords = [(p.lon, p.lat)], name = POINTS[p.subtype].name, description = "Länge: " + locale.format("%.2f", STAGE.km)+" km")
                newpoint.style = self.STYLES[p.subtype]
            
            f = sf.newfolder(name="Abschnitte")
            for SECTOR in STAGE.subsection:
                newtrack = f.newlinestring(name = "Abschnitt "+str(SECTOR.id+1), description = "Länge: " + locale.format("%.2f", SECTOR.km)+" km")
                newtrack.style = self.STYLES["track"+str(SECTOR.id % 2)]
                for p in SECTOR.points:
                    newtrack.coords.addcoordinates([(p.lon, p.lat)])
                
            f = sf.newfolder(name="Zählpunkte")
            # Nur aktive Punkte werden gespeichert
            for p in (x for x in STAGE.countpoints if x.active == 1):
                newpoint = f.newpoint(coords = [(p.lon, p.lat)], description = POINTS[p.subtype].name)
                newpoint.style = self.STYLES[p.subtype]

            f = sf.newfolder(name="Orientierungskontrollen")
            for p in (x for x in STAGE.checkpoints if x.active == 1):
                newpoint = f.newpoint(coords = [(p.lon, p.lat)], name = p.value, description = POINTS[p.subtype].name)
                newpoint.style = self.STYLES[p.subtype]
                
        self.KML.savekmz(KML_FILE)
        
    def setPointStyle(self, subtype):
        icon = tripmasterPath + "/static/kmz/" + subtype + ".gif"
        newstyle = simplekml.Style()
        newstyle.iconstyle.icon.href = self.KML.addfile(icon)
        return newstyle

if __name__ == "__main__":

    saveKMZ()

