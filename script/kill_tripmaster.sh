#!/bin/bash
cd /home/pi/tripmaster
sudo kill -SIGINT $(cat run.pid)

ret=$?
if [ $ret -ne 0 ]; then
        echo "Es ist ein Fehler aufgetreten: Errorcode $ret"
else
        echo "Tripmaster heruntergefahren"
fi

sleep 3
clear