#!/bin/bash
cd /home/pi/tripmaster/out

echo -e "Verfolge das Tripmaster Log\n"

sudo tail -f ./tripmaster.log

read pause