#!/bin/bash
cd /home/pi/tripmaster
sudo ifconfig wlan1 up

while ! ( ifconfig -s | grep wlan1 ) ; do
    echo "wlan1 noch nicht gestartet, warte 2 Sekunden";
    sleep 2;
done

sudo apt update 
sudo apt -y upgrade 
sudo apt-get autoremove

sudo ifconfig wlan1 down

read pause