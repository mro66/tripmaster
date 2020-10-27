#!/bin/bash

sudo chmod +x ./tripmaster_web.py
sudo chmod +x ./kill_tripmaster.sh
sudo chmod +x ./start_tripmaster.sh
sudo chmod +x ./start_tripmaster_debug.sh
sudo cp ./kill_tripmaster.sh /usr/local/sbin/
sudo cp ./start_tripmaster.sh /usr/local/sbin/
sudo cp ./start_tripmaster_debug.sh /usr/local/sbin/