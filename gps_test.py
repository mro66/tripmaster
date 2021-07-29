#!/usr/bin/env python3

from gps import gps, WATCH_ENABLE
from datetime import datetime, timezone
import time
import threading

gpsd = None #seting the global variable
gpsTimeFormat = '%Y-%m-%dT%H:%M:%S.%fZ'

# Besser als os.system('clear'):
# Cursor an den Bildschirmanfang
print(chr(27) + "[H")
# Bildschirm löschen
print(chr(27) + "[2J")

class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        global gpsd #bring it in scope
        gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
        self.current_value = None
        self.running = True #setting the thread running to true

    def run(self):
        global gpsd
        while gpsp.running:
            gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer

if __name__ == '__main__':
    gpsp = GpsPoller() # create the thread
    try:
        gpsp.start() # start it up
        while True:
            #It may take a second or two to get good data
            #print gpsd.fix.latitude,', ',gpsd.fix.longitude,'  Time: ',gpsd.utc
            
            time_utc = None
            time_local = None
            if (gpsd.utc != None and len(gpsd.utc) > 0):
                time_utc = datetime.strptime(gpsd.utc, gpsTimeFormat)
                time_local = time_utc.replace(tzinfo=timezone.utc).astimezone()
                
            
            print( 'GPS reading')
            print( '----------------------------------------')
            print( 'time local: ' , time_local)
            print( 'time utc:   ' , time_utc)
            print( 'time system:' , datetime.now())
            if time_local is not None:
                td = time_local - datetime.now(time_local.tzinfo)
                td = round(td.total_seconds(), 2)
            else:
                td = 'nan'
            print( 'time diff:  ' , td)
            print( 'latitude:   ' , gpsd.fix.latitude)
            print( 'longitude:  ' , gpsd.fix.longitude)
            print( 'altitude:   ' , gpsd.fix.altitude, 'm')
            print( 'speed:      ' , gpsd.fix.speed, 'm/s')
            print( 'heading:    ' , gpsd.fix.track, 'deg')
            print( 'climb:      ' , gpsd.fix.climb, 'm/min')
            print( 'status:      %s'  % ("NO SIG", "NO FIX", "2D FIX", "3D FIX")[gpsd.fix.mode])
            print( 'longitude err:   +/-' , gpsd.fix.epx, 'm')
            print( 'latitude err:    +/-' , gpsd.fix.epy, 'm')
            print( 'altitude err:    +/-' , gpsd.fix.epv, 'm')
            print( 'course err:      +/-' , gpsd.fix.epd, 'deg')
            print( 'speed err:       +/-' , gpsd.fix.eps, 'm/s')
            print( 'timestamp err:   +/-' , gpsd.fix.ept, 's')
            print('')
            index = 0
            for satellite in gpsd.satellites:
                index += 1
                print ('Sat:', str(index).rjust(2, " "), '', satellite)
            
            print('')
            
            time.sleep(3) #set to whatever
            print(chr(27) + "[H")
            print(chr(27) + "[2J", flush = True)
            # os.system('clear')
            
    except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
        print ("\nKilling Thread...")
        gpsp.running = False
        gpsp.join() # wait for the thread to finish what it's doing
        
        print ("Done.\nExiting."    )