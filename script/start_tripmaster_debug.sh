#!/bin/bash
cd /home/pi/tripmaster

echo -e "Starte den Tripmaster im DEBUG Modus\n"

sudo ./tripmaster_web.py debug

# read pause