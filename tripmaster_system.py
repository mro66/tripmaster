#!/usr/bin/env python3

from datetime import datetime
from gpiozero import CPUTemperature, DigitalOutputDevice, LED
from logging.handlers import RotatingFileHandler
from ina219 import INA219       
from psutil import cpu_percent, virtual_memory
import gpsd
import logging
import os
import sys
import threading


# Programmpfad 
tripmasterPath = os.path.dirname(os.path.abspath(__file__))
# Pfade für die Outputdateien
rallyeFile     = tripmasterPath + '/out/rallye.dat'
trackFile      = tripmasterPath + '/out/track.csv'
outputFile     = tripmasterPath + '/out/output.txt'

### --- Konfiguration des Loggers
logger = logging.getLogger('Tripmaster')
logging.basicConfig(
    handlers=[RotatingFileHandler(tripmasterPath+"/out/tripmaster.log", maxBytes=500000, backupCount=5)],
    format="%(asctime)s.%(msecs)03d %(module)-18s %(lineno)-4s %(levelname)-7s %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S")
logger.setLevel(logging.INFO)

### --- Konfiguration des Debug-Modus
DEBUG = False
# Kommandozeilenargument
if len(sys.argv) > 1:
    DEBUG = (sys.argv[1] == "debug")
if DEBUG:
    logger.setLevel(logging.DEBUG)

logger.info("------------------------------")
logger.info("Starte Tripmaster V5.1")
logger.info("DEBUG: " + str(DEBUG))


### Lüfter (Pin 27)
FAN = DigitalOutputDevice(27)


### Mit dem GPS Daemon verbinden
gpsd.connect()


# Ermitteln des Systemstatus und der GPS Position
class __statusSystem():
    global DEBUG
    def __init__(self):
        ### Systemressourcen
        self.MEM_USED         = 0.0
        self.CPU_LOAD         = 0.0
        self.CPU_TEMP         = 0.0
        self.UBAT             = 0.0
        self.UBAT_CAP         = 2
        # Systemuhr mit GPS synchron?
        self.CLOCK_SYNCED     = False
        # DigitalOutputDevice setzt standardmäßig active_high=True (on() -> HIGH) und initial_value=False (device ist aus)
        # Stacks zum Berechnen eines gleitenden Mittels
        self.__STACK_MEM_USED = []
        self.__STACK_CPU_LOAD = []
        self.__STACK_CPU_TEMP = []
        ### Spannungsmessung
        SHUNT_RESISTANCE      = 0.1
        MAX_CURRENT           = 0.4
        self.__ina            = INA219(SHUNT_RESISTANCE, MAX_CURRENT)
        self.__ina.configure(self.__ina.RANGE_16V, self.__ina.GAIN_1_40MV)
        self.__STACK_UBAT     = []
        ### GPS Status
        self.__DEBUG_GPS      = 0
        self.__GPS_LAST_MODE  = -1
        self.GPS_MODE         = -1
        self.GPS_LAT          = 0.0
        self.GPS_LON          = 0.0
        self.GPS_HSPEED       = 0.0
        self.GPS_CHANGED      = True
        # Wurde noch kein Client gestartet?
        self.__no_clients_yet = True
        # Zweifarbige Status-LED, grün aus, rot an (so kommt sie aus dem System)
        self.__led_green      = LED(19)
        self.__led_red        = LED(26, initial_value=True)
        # Anzahl der Clients, aktuell und beim letzten Durchlauf
        self.__nclients       = 0
        self.__nclients_was_0 = True
        # Wartezeit
        self.__wait           = 2.0

    def setState(self):
        # CPU Auslastung in %
        self.CPU_LOAD = self.__movingAverage(self.__STACK_CPU_LOAD, cpu_percent(), 20)
        # CPU Temperatur in °C
        self.CPU_TEMP = self.__movingAverage(self.__STACK_CPU_TEMP, CPUTemperature().temperature, 20)
        # Speicherauslastung in %
        self.MEM_USED = self.__movingAverage(self.__STACK_MEM_USED, virtual_memory().available / virtual_memory().total * 100, 10)
        # Akkuspannung in V
        ubat          = self.__movingAverage(self.__STACK_UBAT, self.__ina.voltage() + self.__ina.shunt_voltage()/1000, 20)
        # Wenn die Spannungsmessung weniger als 2V liefert, ist _wahrscheinlich_ ein Netzteil am USB Port
        # (sonst würde der Pi nicht laufen)
        if ubat < 2.0:
            ubat = 5.0
        self.UBAT = min(ubat, 5.0)
        # Akkukapazität in %
        # UBAT_CAP * 25 = Prozent Akkukapazität
        if (self.UBAT < 3.20):
            self.UBAT_CAP -= 1 # abschalten!
        elif (self.UBAT < 3.27):
            self.UBAT_CAP = 0 # 0 %
        elif (self.UBAT < 3.58):
            self.UBAT_CAP = 1 # 25 %
        elif (self.UBAT < 3.69):
            self.UBAT_CAP = 2 # 50 %
        elif (self.UBAT < 3.85):
            self.UBAT_CAP = 3 # 75 %
        elif (self.UBAT < 5.0):
            self.UBAT_CAP = 4 # 100 %
        else:
            self.UBAT_CAP = 5 # Netzteil

        # Lüfter an bei CPU Temperaturen über 70°C
        if (self.CPU_TEMP > 70.0):
            FAN.on()
        # Lüfter aus bei CPU Temperaturen unter 58°C
        elif (self.CPU_TEMP < 58.0):
            FAN.off()

        # logger.info("MEM LOAD TEMP BAT CAP: {0:0.2f} {1:0.2f} {2:0.2f} {3:0.2f} {4:}".format(self.MEM_USED, self.CPU_LOAD, self.CPU_TEMP, self.UBAT, self.UBAT_CAP))

        # Die aktuelle GPS-Position ermitteln
        GPScurrent = gpsd.get_current()
        if GPScurrent is not None:
            if (not self.CLOCK_SYNCED) and (GPScurrent.mode >= 2):
                self.CLOCK_SYNCED = True
    
            if DEBUG:
                self.__DEBUG_GPS += 1
                self.GPS_MODE     = 3
                self.GPS_LON      = 10.45 + self.__DEBUG_GPS/5000
                self.GPS_LAT      = 51.16 + self.__DEBUG_GPS/7500
                self.GPS_HSPEED   = 15
                self.GPS_CHANGED  = False
            else:
                self.GPS_MODE   = GPScurrent.mode
                self.GPS_LON    = GPScurrent.lon
                self.GPS_LAT    = GPScurrent.lat
                self.GPS_HSPEED = GPScurrent.hspeed

            # GPS gilt bei Änderung von < 2 auf >=2 und umgekehrt
            self.GPS_CHANGED = (self.__GPS_LAST_MODE == -1 or \
                               (self.__GPS_LAST_MODE < 2 and self.GPS_MODE >=2) or \
                               (self.__GPS_LAST_MODE >=2 and self.GPS_MODE < 2))
            self.__GPS_LAST_MODE = self.GPS_MODE
            
        if DEBUG:
            # Systemvariable speichern: Genutztes RAM, CPU Last, CPU Temperatur, Spannung
            var = [self.MEM_USED, self.CPU_LOAD, self.CPU_TEMP, self.UBAT]
            with open(outputFile, 'a') as of:
                of.write('{:}'.format(datetime.now().strftime('%d.%m.%Y %H:%M:%S')))
                for v in var:
                    of.write('\t{:0.4f}'.format(v).replace('.', ','))
                of.write('\n')
    
    def __movingAverage(self, stack, newval, maxlength):
        # Neuen Wert am Ende des Stacks einfügen
        stack.append(newval)
        if len(stack) > maxlength:
            # Erstes Element entfernen, wenn maximale Länge des Stacks überschritten wird
            stack.pop(0)
        # Mittelwert des Stacks zurückgeben
        return sum(stack) / len(stack)

    def checkLED(self):       
        # Steuerung der Status-LED i.A.v. GPS-Modus und der Anzahl der verbundenen Clients
        # Ohne Clients
        if self.__nclients == 0:
            
            # LEDs nur ändern, wenn sich der GPS-Modus geändert hat (flackern sonst)
            if self.GPS_CHANGED:
                # Wenn mindestens ein 2D Fix, ...
                if (self.GPS_MODE >= 2):
                    logger.debug('GRÜN blinkt (GPS Mode %s)', self.GPS_MODE)
                    # ... dann blinkt die grüne LED
                    self.__led_red.off()
                    self.__led_green.blink()
                else:
                    logger.debug(' ROT blinkt (GPS Mode %s)', self.GPS_MODE)
                    # ... ansonsten blinkt die rote LED
                    self.__led_green.off()
                    self.__led_red.blink()

                # Anzahl der Clients ist beim nächsten Durchlauf null
                self.__nclients_was_0 = True

            # Systemstatus überprüfen, jedoch nur so lange sich nicht wenigstens einmal ein Client verbunden hat
            # Danach läuft immer ein Tripmaster Timer-Thread, der das erledigt
            if self.__no_clients_yet:
                self.setState()
        # Mit Clients
        else:
            # LEDs nur ändern, wenn die Anzahl der Clients im letzten Durchlauf null war (flackern sonst)
            if self.__nclients_was_0:
                self.__led_red.off()
                self.__led_green.on()
                logger.debug('GRÜN permanent')
                # Anzahl der Clients ist beim nächsten Durchlauf nicht null
                self.__nclients_was_0 = False

        timed        = threading.Timer(self.__wait, self.checkLED)
        timed.daemon = True
        timed.start()
        # logger.debug('checkLED alle %s Sekunden', self.__wait)
            
    def setNClients(self, n):
        if n > 0:
            # Schaltet die Überprüfung des Systemstatus in diesem Thread ab (s.o.)
            self.__no_clients_yet = False
            # Seltener aktualisieren, wenn Clients verbunden sind
            self.__wait = 10.0
        else:
            # Häufiger aktualisieren, wenn keine Clients verbunden sind
            self.__wait = 2.0
        self.__nclients_was_0 = (self.__nclients == 0)
        self.__nclients = n
        
    def releaseLEDs(self):
        self.__led_green.close()
        self.__led_red.close()

# System initialisieren
SYSTEM = __statusSystem()
# Thread zur Steuerung der Status-LED
timed        = threading.Timer(2.0, SYSTEM.checkLED)
timed.daemon = True
timed.start()
logger.debug("Thread für den GPS-Status gestartet")
