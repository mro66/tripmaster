#!/bin/bash
cd /home/pi/tripmaster
sudo kill -9 $(cat run.pid)

sleep 3