#!/bin/bash

sudo cp ./*.sh /usr/local/sbin/
sudo cp ./*.desktop /home/pi/Desktop/
sudo chmod -R 777 ../tripmaster_web.py
sudo chmod -R 777 /usr/local/sbin/*.sh
sudo chmod -R 777 /home/pi/Desktop/*.desktop
