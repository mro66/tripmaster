#!/bin/bash

sudo chmod -R 777 ./picontrol
sudo cp ./picontrol /usr/local/sbin/
sudo chmod -R 777 ../tripmaster_web.py
sudo chmod -R 777 ./*.sh
