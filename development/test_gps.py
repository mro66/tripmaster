#!/usr/bin/env python3

import gpsd

# Connect to the local gpsd
gpsd.connect()

# Connect somewhere else
gpsd.connect()

# Get gps position
GPS_CURRENT = gpsd.get_current()

# See the inline docs for GpsResponse for the available data
print(" ************ PROPERTIES ************* ")
print("  Mode: " + str(GPS_CURRENT.mode))
print("Satellites: " + str(GPS_CURRENT.sats))
if GPS_CURRENT.mode >= 2:
    print("  Latitude: " + str(GPS_CURRENT.lat))
    print(" Longitude: " + str(GPS_CURRENT.lon))
    print(" Track: " + str(GPS_CURRENT.track))
    print("  Horizontal Speed: " + str(GPS_CURRENT.hspeed))
    print(" Time: " + str(GPS_CURRENT.time))
    print(" Error: " + str(GPS_CURRENT.error))
else:
    print("  Latitude: NOT AVAILABLE")
    print(" Longitude: NOT AVAILABLE")
    print(" Track: NOT AVAILABLE")
    print("  Horizontal Speed: NOT AVAILABLE")
    print(" Error: NOT AVAILABLE")

if GPS_CURRENT.mode >= 3:
    print("  Altitude: " + str(GPS_CURRENT.alt))
    print(" Climb: " + str(GPS_CURRENT.climb))
else:
    print("  Altitude: NOT AVAILABLE")
    print(" Climb: NOT AVAILABLE")

print(" ************** METHODS ************** ")
if GPS_CURRENT.mode >= 2:
    print("  Location: " + str(GPS_CURRENT.position()))
    print(" Speed: " + str(GPS_CURRENT.speed()))
    print("Position Precision: " + str(GPS_CURRENT.position_precision()))
    print("   Map URL: " + str(GPS_CURRENT.map_url()))
else:
    print("  Location: NOT AVAILABLE")
    print(" Speed: NOT AVAILABLE")
    print("Position Precision: NOT AVAILABLE")
    print("  Time UTC: NOT AVAILABLE")
    print("Time Local: NOT AVAILABLE")
    print("   Map URL: NOT AVAILABLE")

if GPS_CURRENT.mode >= 3:
    print("  Altitude: " + str(GPS_CURRENT.altitude()))
    # print("  Movement: " + str(GPS_CURRENT.movement()))
    # print("  Speed Vertical: " + str(GPS_CURRENT.speed_vertical()))
else:
    print("  Altitude: NOT AVAILABLE")
    # print("  Movement: NOT AVAILABLE")
    # print(" Speed Vertical: NOT AVAILABLE")

print(" ************* FUNCTIONS ************* ")
print("Device: " + str(gpsd.device()))