# import simplekml

Geodatenausgabe als KML und/oder CSV
# KML = None

Styles
# TRACK_RED = simplekml.Style()
# TRACK_RED.linestyle.width = 5
# TRACK_RED.linestyle.color = "ff4f53d9"

# TRACK_GREEN = simplekml.Style()
# TRACK_GREEN.linestyle.width = 5
# TRACK_GREEN.linestyle.color = "ff5cb85c"

Folders
# FOLDER_STAGE = None
# FOLDER_SECTORTRACKS = None
# FOLDER_COUNTPOINTS = None
# FOLDER_CHECKPOINTS = None

# FOLDERS = {
    # "stage": FOLDER_STAGE,
    # "sectortrack": FOLDER_SECTORTRACKS,
    # "countpoint": FOLDER_COUNTPOINTS,
    # "checkpoint": FOLDER_CHECKPOINTS,
    # }

class POINT:
    def __init__(self, name, icon, iconcolor, mapicon = ""):
        # self.name = name
        # self.icon = icon
        # self.iconcolor = "var(--tm-" + iconcolor + ")"
        # self.mapicon = mapicon
        # enabledIcon = tripmasterPath + "/static/kmz/" + self.mapicon + ".gif"
        # disabledIcon = tripmasterPath + "/static/kmz/" + self.mapicon + "_disabled.gif"
        if os.path.exists(enabledIcon):
            self.style = None
            self.style = simplekml.Style()
            self.style.iconstyle.icon.href = KML.addfile(enabledIcon)
        if os.path.exists(disabledIcon):
            self.disabledstyle = None
            self.disabledstyle = simplekml.Style()
            self.disabledstyle.iconstyle.icon.href = KML.addfile(disabledIcon)

def getStyleByName(name, visibility):
    for P in POINTS:
        if POINTS[P].name == name:
            if visibility == 1:
                return POINTS[P].style
            else:
                return POINTS[P].disabledstyle

# Etappe initialisieren
def initStage(LON, LAT):
    global FOLDERS, STAGE, SECTOR
    # STAGE.no += 1
    FOLDERS["stage"] = KML.newfolder(name="Etappe " + str(STAGE.no))
    FOLDERS["sectortrack"] = FOLDERS["stage"].newfolder(name="Abschnitte")
    FOLDERS["countpoint"] = FOLDERS["stage"].newfolder(name="Zählpunkte")
    FOLDERS["checkpoint"] = FOLDERS["stage"].newfolder(name="Orientierungskontrollen")
    setPoint(FOLDERS["stage"], POINTS["stage_start"].style, LON, LAT, "", POINTS["stage_start"].name)    

def initSector(LON, LAT):
    global KML_FILE, SECTOR, REVERSE
    if SECTOR.no > 1:
        Alten Abschnitt mit den aktuellen Koordinaten abschließen
        SECTOR.track.coords.addcoordinates([(LON,LAT)])
        KML.savekmz(KML_FILE)
    # Neuen Abschnitt beginnen
    SECTOR.track = FOLDERS["sectortrack"].newlinestring(name="Abschnitt "+str(SECTOR.no))
    if (SECTOR.no % 2 == 0):
        SECTOR.track.style = TRACK_RED
    else:
        SECTOR.track.style = TRACK_GREEN
    SECTOR.track.coords.addcoordinates([(LON,LAT)])
    KML.savekmz(KML_FILE)

def setPoint(POINTFOLDER, POINTSTYLE, LON, LAT, DESCRIPTION, NAME=""):
    global KML_FILE
    NEWPOINT = POINTFOLDER.newpoint(coords=[(LON,LAT)], description = DESCRIPTION, name = NAME, visibility = 1)
    NEWPOINT.style = POINTSTYLE
    KML.savekmz(KML_FILE)

def initRallye():
    global KML, KML_FILE
    # KML = simplekml.Kml(open=1)
    # KML_FILE = tripmasterPath+"/out/{0:%Y%m%d_%H%M}.kmz".format(datetime.now());
