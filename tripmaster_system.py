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
import os
import subprocess
import time


### Mit dem GPS Daemon verbinden
gpsd.connect()

### --- Konfiguration Logger und Output ---
# Programmpfad 
tripmasterPath = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    handlers=[RotatingFileHandler(tripmasterPath+"/out/tripmaster.log", maxBytes=500000, backupCount=5)],
    format="%(asctime)s.%(msecs)03d %(module)-18s %(lineno)-4s %(levelname)-7s %(message)s",
    datefmt="%d.%m.%Y %H:%M:%S")
logger = logging.getLogger('Tripmaster')
# Pfade für die Outputdateien
rallyeFile = tripmasterPath + '/out/rallye.dat'
trackFile  = tripmasterPath + '/out/track.csv'
outputFile = tripmasterPath + '/out/output.txt'

# Status der Systemparameter (z.T. als gleitende Mittel) und Kontrolle der Status-LED
class getSystemState(Thread):
    def __init__(self):
        Thread.__init__(self)
        # Zweifarbige Status-LED, grün aus, rot an (so kommt sie aus dem System)
        self.__led_green       = LED(19)
        self.__led_red         = LED(26, initial_value=True)
        # DigitalOutputDevice setzt standardmäßig active_high=True (on() -> HIGH) und initial_value=False (device ist aus)
        # Der Lüfter an Pin 27 
        self.__fan             = DigitalOutputDevice(27)
        # Systemuhr mit GPS synchron?
        self.CLOCK_SYNCED      = False
        # Systemparameter
        self.MEM_USED          = 0.0
        self.__STACK_MEM_USED  = []
        self.CPU_LOAD          = 0.0
        self.__STACK_CPU_LOAD  = []
        self.CPU_TEMP          = 0.0
        self.__STACK_CPU_TEMP  = []
        ### Spannungsmessung
        SHUNT_RESISTANCE = 0.1
        MAX_CURRENT = 0.4
        self.ina = INA219(SHUNT_RESISTANCE, MAX_CURRENT)
        self.ina.configure(self.ina.RANGE_16V, self.ina.GAIN_1_40MV)
        self.UBAT              = 0.0
        self.__STACK_UBAT      = []
        self.UBAT_CAP          = 0
        # Anzahl der Clients
        self.__nclients        = 0
        # Hat sich der GPS-Modus und die Anzahl Clients geändert?
        self.__gpschanged      = True
        self.__nclientschanged = True

    def run(self):
        while True:
            GPScurrent = gpsd.get_current()
            
            # CPU Auslastung in %
            self.CPU_LOAD = self.__movingAverage(self.__STACK_CPU_LOAD, cpu_percent(), 20)
            # CPU Temperatur in °C
            self.CPU_TEMP = self.__movingAverage(self.__STACK_CPU_TEMP, CPUTemperature().temperature, 20)
            # Speicherauslastung in %
            self.MEM_USED = self.__movingAverage(self.__STACK_MEM_USED, virtual_memory().available / virtual_memory().total * 100, 10)
            # Akkuspannung in V
            ubat = self.__movingAverage(self.__STACK_UBAT, self.ina.voltage() + self.ina.shunt_voltage()/1000, 20)
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

            # logger.info("MEM LOAD TEMP BAT CAP: {0:0.2f} {1:0.2f} {2:0.2f} {3:0.2f} {4:}".format(self.MEM_USED, self.CPU_LOAD, self.CPU_TEMP, self.UBAT, self.UBAT_CAP))
        
            if (not self.CLOCK_SYNCED):
                if (len(GPScurrent.time) == 24):
                    naive = datetime.strptime(GPScurrent.time, '%Y-%m-%dT%H:%M:%S.%fZ')
                    utc   = timezone('UTC').localize(naive)
                    local = utc.astimezone(timezone('Europe/Berlin'))
                    subprocess.call("sudo date -u -s '"+str(local)+"' > /dev/null 2>&1", shell=True)
                    self.CLOCK_SYNCED = True
                    logger.info("Systemzeit wurde mit GPS sychronisiert")
                else:
                    self.CLOCK_SYNCED = False
                    logger.info("Systemzeit nicht mit GPS synchron")
        
            # Lüfter an bei CPU Temperaturen über 70°C
            if (self.CPU_TEMP > 70.0):
                self.__fan.on()
            # Lüfter aus bei CPU Temperaturen unter 58°C
            elif (self.CPU_TEMP < 58.0):
                self.__fan.off()
    
            # if DEBUG:
                # saveOutput([self.MEM_USED, self.CPU_LOAD, self.CPU_TEMP, self.UBAT])
            
            # Steuerung der Status-LED
            # Ohne Clients
            if (self.__nclients == 0):
                # logger.info('GPS Mode: ' + str(GPScurrent.mode))
                # LEDs nur ändern, wenn sich der GPS-Modus geändert hat (flackern sonst)
                if (self.__gpschanged):
                    # Wenn mindestens ein 2D Fix, ...
                    if (GPScurrent.mode >= 2):
                        logger.info('GPS.mode >= 2 -> GRÜN blinkt ab jetzt')
                        # ... dann blinkt die grüne LED
                        self.__led_red.off()
                        self.__led_green.blink()
                    else:
                        logger.info('GPS.mode < 2 -> ROT blinkt ab jetzt')
                        # ... ansonsten blinkt die rote LED
                        self.__led_green.off()
                        self.__led_red.blink()
                self.__gpschanged = ((self.__led_green.is_active and GPScurrent.mode < 2) or \
                                   (self.__led_red.is_active   and GPScurrent.mode >= 2))
            # Mit Clients
            else:
                # LEDs nur ändern, wenn sich die Anzahl der Clients geändert hat (flackern sonst)
                if (self.__nclientschanged):
                    self.__led_green.on()
                    self.__led_red.off()
                    self.__gpschanged = True
                    logger.info('GRÜN ab jetzt dauerhaft an')
                self.__nclientschanged = (self.__nclients == 0)
            
            time.sleep(2)
            
    def __movingAverage(self, stack, newval, maxlength):
        # Neuen Wert am Ende des Stacks einfügen
        stack.append(newval)
        if len(stack) > maxlength:
            # Erstes Element entfernen, wenn maximale Länge des Stacks überschritten wird
            stack.pop(0)
        # Mittelwert des Stacks zurückgeben
        return sum(stack) / len(stack)
    
    def setNClients(self, n):
        self.__nclients = n
        
    def releaseLEDs(self):
        self.__led_green.close()
        self.__led_red.close()

def saveOutput(var):
    with open(outputFile, 'a') as of:
        of.write('{:}'.format(datetime.now().strftime('%d.%m.%Y %H:%M:%S')))
        for v in var:
            of.write('\t{:0.4f}'.format(v).replace('.', ','))
        of.write('\n')

