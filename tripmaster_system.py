#!/usr/bin/env python3

from datetime import datetime
from gpiozero import CPUTemperature, DigitalOutputDevice, LED
from logging.handlers import RotatingFileHandler
from ina219 import INA219       
from psutil import cpu_percent, virtual_memory
from pytz import timezone
from threading import Thread
import gpsd
import logging
import math
import os
import subprocess
import sys
import time


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
logger.info("Starte Tripmaster V4.0")
logger.info("DEBUG: " + str(DEBUG))

### Lüfter (Pin 27)
FAN = DigitalOutputDevice(27)

# Berechnen der Systemresourcen
class __system():
    global DEBUG
    def __init__(self, debug):
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
    
        if (DEBUG):
            # Systemvariable speichern: Genutztes RAM, CPU Last, CPU Temperatur, Spannung
            var = [self.MEM_USED, self.CPU_LOAD, self.CPU_TEMP, self.UBAT]
            with open(outputFile, 'a') as of:
                of.write('{:}'.format(datetime.now().strftime('%d.%m.%Y %H:%M:%S')))
                for v in var:
                    of.write('\t{:0.4f}'.format(v).replace('.', ','))
                of.write('\n')
        
        # Synchronisation der Systemuhr mit GPS
        if (not self.CLOCK_SYNCED):
            GPScurrent = getGPSCurrent()
            if (len(GPScurrent.time) == 24):
                naive = datetime.strptime(GPScurrent.time, '%Y-%m-%dT%H:%M:%S.%fZ')
                utc   = timezone('UTC').localize(naive)
                local = utc.astimezone(timezone('Europe/Berlin'))
                subprocess.call("sudo date -u -s '"+str(local)+"' > /dev/null 2>&1", shell=True)
                self.CLOCK_SYNCED = True
                logger.info("Systemuhr wurde mit GPS sychronisiert")
            else:
                logger.warning("Systemuhr nicht mit GPS synchron")

    def __movingAverage(self, stack, newval, maxlength):
        # Neuen Wert am Ende des Stacks einfügen
        stack.append(newval)
        if len(stack) > maxlength:
            # Erstes Element entfernen, wenn maximale Länge des Stacks überschritten wird
            stack.pop(0)
        # Mittelwert des Stacks zurückgeben
        return sum(stack) / len(stack)

SYSTEM = __system(True)


### Steuerung der Status-LED
class statusLED(Thread):
    global SYSTEM, DEBUG
    def __init__(self):
        Thread.__init__(self)
        # Wurde noch kein Client gestartet?
        self.__no_clients_yet = True
        # Zweifarbige Status-LED, grün aus, rot an (so kommt sie aus dem System)
        self.__led_green      = LED(19)
        self.__led_red        = LED(26, initial_value=True)
        # GPS-Modus der LED beim letzten Durchlauf
        self.__last_gps       = -1
        # Anzahl der Clients, aktuell und beim letzten Durchlauf
        self.__nclients       = 0
        self.__last_nclients  = 0
        # Status der Zeitsynchronisation beim letzten Durchlauf
        self.__last_clocksync = False
        # 'Schlafenszeit'
        self.__timetosleep    = 2

    def run(self):
        while True:        
            GPScurrent = getGPSCurrent()
            now = datetime.utcnow()
            if (len(GPScurrent.time) == 24):
                gpsnow = datetime.strptime(GPScurrent.time, '%Y-%m-%dT%H:%M:%S.%fZ')
                logger.debug('time offset: %s', (gpsnow - now).total_seconds())
                if abs((gpsnow - now).total_seconds()) > 0.2:
                    SYSTEM.CLOCK_SYNCED = False


            
            # Seit dem letzten Durchlauf:
            # Hat sich das GPS-Signal geändert?
            hasGPSchanged = (self.__last_gps == -1 or \
                            (self.__last_gps < 2 and GPScurrent.mode >=2) or \
                            (self.__last_gps >=2 and GPScurrent.mode < 2))
            # Hat sich die Anzahl der Clients geändert?
            hasnClientschanged = (self.__last_nclients == 0)
            # Wurde die Systemuhr synchronisiert
            hasClocksynced = (SYSTEM.CLOCK_SYNCED != self.__last_clocksync)
            
            # logger.debug('nclients: %s, hasGPSchanged: %s, last_gps: %s', self.__nclients, hasGPSchanged, self.__last_gps)
            
            # Steuerung der Status-LED i.A.v. GPS-Modus und der Anzahl der verbundenen Clients
            # Ohne Clients
            if (self.__nclients == 0):
                # logger.info('GPS Mode: ' + str(GPScurrent.mode))
                # LEDs nur ändern, wenn sich der GPS-Modus geändert hat (flackern sonst)
                if (hasGPSchanged):
                    # Wenn mindestens ein 2D Fix, ...
                    if (GPScurrent.mode >= 2):
                        logger.debug('GRÜN blinkt (GPS vorher: %s, jetzt: %s)', self.__last_gps, GPScurrent.mode)
                        # ... dann blinkt die grüne LED
                        self.__led_red.off()
                        self.__led_green.blink()
                    else:
                        logger.debug(' ROT blinkt (GPS vorher: %s, jetzt: %s)', self.__last_gps, GPScurrent.mode)
                        # ... ansonsten blinkt die rote LED
                        self.__led_green.off()
                        self.__led_red.blink()

                    # Häufiger aktualisieren, wenn keine Clients verbunden sind
                    self.__timetosleep = 2
                    # Anzahl der Clients zurücksetzen
                    self.__last_nclients = 0
                    # Zustand sichern: GPS-Modus
                    self.__last_gps = GPScurrent.mode
                    
                # Systemstatus überprüfen, jedoch nur so lange sich nicht wenigstens einmal ein Client verbunden hat
                # Danach läuft immer ein Tripmaster Timer-Thread, der das erledigt
                if self.__no_clients_yet:
                    SYSTEM.setState()
            # Mit Clients
            else:
                # Schaltet die Überprüfung des Systemstatus in diesem Thread ab (s.o.)
                self.__no_clients_yet = False
                # LEDs nur ändern, wenn sich die Anzahl der Clients geändert hat (flackern sonst)
                if (hasnClientschanged or hasClocksynced):
                    if (SYSTEM.CLOCK_SYNCED):
                        self.__led_red.off()
                        self.__led_green.on()
                        logger.debug('GRÜN permanent')
                    else:
                        self.__led_green.blink()
                        time.sleep(1)
                        self.__led_red.blink()
                        logger.debug('ROT-GRÜN wechselblinken')
                    if (hasnClientschanged):
                        # Seltener aktualisieren, wenn Clients verbunden sind
                        self.__timetosleep = 10
                        # GPS-Modus zurücksetzen
                        self.__last_gps = -1
                        # Zustand sichern: Anzahl der Clients
                        self.__last_nclients = self.__nclients

            # Zustand sichern: Synchronisation der Systemuhr
            self.__last_clocksync = SYSTEM.CLOCK_SYNCED
            time.sleep(self.__timetosleep)
            
    def setNClients(self, n):
        self.__nclients = n
        
    def releaseLEDs(self):
        self.__led_green.close()
        self.__led_red.close()

# Thread zur Steuerung der Status-LED
ThreadLED = statusLED()
# While a non-daemon thread blocks the main program to exit if they are not dead.
# A daemon thread runs without blocking the main program from exiting.
ThreadLED.daemon = True


### Mit dem GPS Daemon verbinden
gpsd.connect()
# Index für künstlichen GPS-Fix
DEBUG_GPS_INDEX = 0

# Ermittelt die aktuelle GPS-Position
def getGPSCurrent():
    global DEBUG, DEBUG_GPS_INDEX
    # Aktuelle Position
    gps_current = gpsd.get_current()
    if DEBUG:
        DEBUG_GPS_INDEX   += 1
        gps_current.mode   = 3
        gps_current.lon    = 10.45 + DEBUG_GPS_INDEX/5000
        gps_current.lat    = 51.16 + DEBUG_GPS_INDEX/7500
        gps_current.hspeed = 15
    return gps_current

