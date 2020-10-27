#!/bin/bash
cd /home/pi/tripmaster/out

echo -e "Verfolge das Tripmaster stderr/stdout\n"

sudo tail -f ./tripmaster.out

read pause