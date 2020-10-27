#!/usr/bin/env python
#coding: utf8 
 
import RPi.GPIO as GPIO
 
# Zählweise der Pins festlegen
GPIO.setmode(GPIO.BCM)

#PIN = 17 # weiß
PIN = 18 # blau

# GPIO 24 als Eingang festlegen
GPIO.setup(PIN, GPIO.IN)
 
# Schleifenzähler
i = 0
 
# Endlosschleife
while 1:
    # Eingang lesen
    if GPIO.input(PIN) == GPIO.LOW:
        # Wenn Eingang LOW ist, Ausgabe im Terminal erzeugen
        print("Eingang LOW " + str(i))
        # Schleifenzähler erhöhen
        i = i + 1
