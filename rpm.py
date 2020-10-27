from time import sleep
import pigpio
from read_RPM import reader
import RPi.GPIO as GPIO

# Einrichten der BCM GPIO Nummerierung
GPIO.setmode(GPIO.BCM)

# Verbinden mit pigpio
pi = pigpio.pi() 
# Einrichten des UMIN readers
REED_GPIO = 14
UMIN_READER = reader(pi, REED_GPIO)

# Messen alle ... Sekunden
SAMPLE_TIME = 2.0
# Messzeitpunkt
T = 0.0
# Umdrehungen pro Minute
UMIN = 0.0
# Geschwindigkeit in Meter pro Sekunde
MS = 0.0
# Reifenumfang
U = 1.2
# Geschwindigkeit in Kilometer pro Stunde
KMH = 0.0
# Durchschnittliche km/h
D_KMH = 0.0
# Zurückgelegte Kilometer
KM = 0.0

print("T\tUmin\tkm/h\tavg km/h\tkm")
try:
    while 1:
        # UMIN ermitteln
        UMIN = int(UMIN_READER.RPM() + 0.5)
        MS = UMIN / 60 * U
        KMH = MS * 3.6
        KM += MS * SAMPLE_TIME / 1000
        if T > 0.0:
            D_KMH = KM * 1000 / T * 3.6
        
        print("{0:0.1f}\t{1}\t{2:0.1f}\t{3:0.1f}\t{4:0.3f}".format(T, UMIN, KMH, D_KMH, KM))
        
        sleep(SAMPLE_TIME)
        T = T + SAMPLE_TIME
        
except KeyboardInterrupt:
    print("KeyboardInterrupt");

finally:
    pi.stop() # Disconnect pigpio.
    print("Sauber beendet!")
