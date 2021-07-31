#!/bin/bash

######################################################################
# tested on RPi4B and 2020-05-27-raspios-buster-armhf.zip


##################################################################
BACKUP_FILE=backup.tar.xz
BACKUP_TRANSFORM=s/^/$(date +%Y-%m-%dT%H_%M_%S)-tripmaster\\//

do_backup() {
    tar -ravf "$BACKUP_FILE" --transform="$BACKUP_TRANSFORM" -C / "$1" &>/dev/null
}


##################################################################
SCRIPT_DIR=`dirname "${BASH_SOURCE[0]}"`
if ! [ -d "$SCRIPT_DIR/etc/chrony/tripmaster" ]; then
    echo -e "\e[1;31m'$SCRIPT_DIR'\e[0m";
    echo -e "\e[1;31mcan not find required files\e[0m";
    exit 1
fi


######################################################################
handle_update() {
    clear
    echo -e "\e[32mhandle_update()\e[0m";

    sudo sync \
    && echo -e "\e[32mupdate...\e[0m" && sudo apt update \
    && echo -e "\e[32mupgrade...\e[0m" && sudo apt full-upgrade -y \
    && echo -e "\e[32mautoremove...\e[0m" && sudo apt autoremove -y --purge \
    && echo -e "\e[32mautoclean...\e[0m" && sudo apt autoclean \
    && echo -e "\e[32mDone.\e[0m" \
    && sudo sync;
    
    # Treiberaktualisierung des USB-WLAN-Adapters (muss zur Kernelversion passen)
    # Installationsskript wurde in Schritt 1 heruntergeladen
    sudo install-wifi  

}


######################################################################
handle_gps() {
    echo -e "\e[32mhandle_gps()\e[0m";

    ##################################################################
    echo -e "\e[36m    prepare GPS\e[0m";
    ##################################################################
    echo -e "\e[36m    setup serial port: /dev/ttyAMA0\e[0m";
    sudo raspi-config nonint do_serial 2;
    sudo systemctl disable --now hciuart;

    ##################################################################
    echo -e "\e[36m    install gpsd\e[0m";
    sudo apt-get -y install gpsd;

    # MRO Clients brauchen ca. 100 MB und sind für den Tripmaster unnötig
    # MRO sudo apt-get -y install gpsd-clients;
    # MRO Diese Bibliothek stellt auch etwas 'grafisches' zur Verfügung
    # MRO sudo apt-get -y install --no-install-recommends python-gi-cairo;
    # MRO Bei OS Lite ist pip nicht in der Distribution enthalten
    echo -e "\e[36m    install python3-pip\e[0m";
    sudo apt-get install python3-pip -y
    # MRO Python3 GPS Daemon installieren: Tripmaster
    echo -e "\e[36m    install gpsd-py3\e[0m";
    sudo python3 -m pip install gpsd-py3
    # MRO Python GPS Daemon installieren: gps_test
    echo -e "\e[36m    install gps[0m";
    sudo python3 -m pip install gps

    sudo usermod -a -G dialout $USER

    ##################################################################
    echo -e "\e[36m    setup gpsd\e[0m";
    sudo systemctl stop gpsd.*;

    do_backup etc/default/gpsd
    cat << EOF | sudo tee /etc/default/gpsd &>/dev/null
# /etc/default/gpsd
## mod_install_stratum_one

# Default settings for the gpsd init script and the hotplug wrapper.

# Start the gpsd daemon automatically at boot time
START_DAEMON="true"

# Use USB hotplugging to add new USB devices automatically to the daemon
USBAUTO="false"

# Devices gpsd should collect to at boot time.
# They need to be read/writeable, either by user gpsd or the group dialout.
DEVICES="/dev/ttyAMA0 /dev/pps0"
# in case you have two pps devices connected
#DEVICES="/dev/ttyAMA0 /dev/pps0 /dev/pps1"

# Other options you want to pass to gpsd
GPSD_OPTIONS="-n -r"
EOF

    ##################################################################
    grep -q mod_install_stratum_one /lib/systemd/system/gpsd.socket &>/dev/null || {
        echo -e "\e[36m    fix gpsd to listen to all connection requests\e[0m";
        do_backup lib/systemd/system/gpsd.socket
        sudo sed /lib/systemd/system/gpsd.socket -i -e "s/^ListenStream=\[::1\]:2947/ListenStream=2947/";
        sudo sed /lib/systemd/system/gpsd.socket -i -e "s/^ListenStream=127.0.0.1:2947/#ListenStream=0.0.0.0:2947/";
        cat << EOF | sudo tee -a /lib/systemd/system/gpsd.socket &>/dev/null
;; mod_install_stratum_one
EOF
    }

    sudo systemctl daemon-reload;
    sudo systemctl enable gpsd;
    sudo systemctl restart gpsd;

    [ -f "/etc/dhcp/dhclient-exit-hooks.d/ntp" ] && {
        do_backup etc/dhcp/dhclient-exit-hooks.d/ntp
        sudo rm -f /etc/dhcp/dhclient-exit-hooks.d/ntp;
    }
}


######################################################################
handle_pps() {
    echo -e "\e[32mhandle_pps()\e[0m";

    ##################################################################
    echo -e "\e[36m    install PPS tools\e[0m";
    sudo apt-get -y install pps-tools;

    ##################################################################
    grep -q pps-gpio /boot/config.txt &>/dev/null || {
        echo -e "\e[36m    setup config.txt for PPS\e[0m";
        do_backup boot/config.txt
        cat << EOF | sudo tee -a /boot/config.txt &>/dev/null

[all]
#########################################
# https://www.raspberrypi.org/documentation/configuration/config-txt.md
# https://github.com/raspberrypi/firmware/tree/master/boot/overlays
## mod_install_stratum_one

# gps + pps + ntp settings

#Name:   disable-bt
#Info:   Disable onboard Bluetooth on Pi 3B, 3B+, 3A+, 4B and Zero W, restoring
#        UART0/ttyAMA0 over GPIOs 14 & 15.
#        N.B. To disable the systemd service that initialises the modem so it
#        doesn't use the UART, use 'sudo systemctl disable hciuart'.
#Load:   dtoverlay=disable-bt
#Params: <None>
dtoverlay=disable-bt


#Name:   pps-gpio
#Info:   Configures the pps-gpio (pulse-per-second time signal via GPIO).
#Load:   dtoverlay=pps-gpio,<param>=<val>
#Params: gpiopin                 Input GPIO (default "18")
#        assert_falling_edge     When present, assert is indicated by a falling
#                                edge, rather than by a rising edge (default
#                                off)
#        capture_clear           Generate clear events on the trailing edge
#                                (default off)
# note, the last listed entry will become /dev/pps0
#
#dtoverlay=pps-gpio,gpiopin=7,capture_clear  # /dev/pps1
dtoverlay=pps-gpio,gpiopin=4,capture_clear  # /dev/pps0

# LED an GPIO26 (rot) beim Booten einschalten
gpio=26=op,dh

# Fast boot options
dtoverlay=sdtweak,overclock_50=100
disable_splash=1
boot_delay=0
dtparam=audio=off
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on

EOF
    }

    ##################################################################
    grep -q pps-gpio /etc/modules &>/dev/null || {
        echo -e "\e[36m    add pps-gpio to modules for PPS\e[0m";
        do_backup etc/modules
        echo 'pps-gpio' | sudo tee -a /etc/modules &>/dev/null
    }
}


######################################################################
install_chrony() {
    echo -e "\e[32minstall_chrony()\e[0m";
    sudo apt-get -y install chrony;
    # MRO gnuplot ist für grafische Desktops
    # MRO sudo apt install -y --no-install-recommends gnuplot;
}


######################################################################
setup_chrony() {
    echo -e "\e[32msetup_chrony()\e[0m";

    sudo systemctl stop chrony;

    do_backup etc/chrony/chrony.conf
    sudo mv /etc/chrony/chrony.conf{,.original}

    sudo cp -Rv $SCRIPT_DIR/etc/chrony/* /etc/chrony/;

    sudo systemctl enable chrony;
    sudo systemctl restart chrony;
}


# MRO ################################################################
install_tripmaster() {
    echo -e "\e[32minstall_tripmaster()\e[0m";
    echo -e "\e[36m    install simplekml\e[0m";
    sudo python3 -m pip install simplekml
    
    echo -e "\e[36m    install pigpio\e[0m";
    sudo apt-get install python3-pigpio -y
    sudo pigpiod
    sudo systemctl enable --now pigpiod
    
    echo -e "\e[36m    install pi-ina219\e[0m";
    sudo raspi-config nonint do_i2c 0
    sudo apt-get install i2c-tools -y
    sudo i2cdetect -y 1
    sudo python3 -m pip install pi-ina219
    
    echo -e "\e[36m    install psutil\e[0m";
    sudo python3 -m pip install psutil
    
    echo -e "\e[36m    install tornado 4.5.3.\e[0m";
    # aktuelle Version
    # sudo apt-get install python3-tornado
    sudo python3 -m pip install tornado==4.5.3.
    
    echo -e "\e[36m    make scripts executable\e[0m";
    cd /home/pi/tripmaster/script/
    sudo chmod +x ./chmod_cp_scripts.sh
    sudo ./chmod_cp_scripts.sh

    echo -e "\e[36m    disable wlan1 at boot\e[0m";
    cd /home/pi/
    sudo crontab -l > tempcron
    echo "@reboot sudo sleep 60 && sudo ifconfig wlan1 down" >> tempcron
    sudo crontab tempcron
    rm tempcron
    
    echo -e "\e[36m    configure autostart\e[0m";
    # In der *€!$$* rc.local steht _zwei Mal_ 'exit 0', daher muss das erste Vorkommen in 'exit_0' umbenannt werden
    sudo sed -i 's/\"exit 0\"/\"exit_0\"/g' /etc/rc.local
    
    # Vor dem zweiten Vorkommen von 'exit 0' die benötigten Befehle eintragen
    sudo sed -i '/exit 0/i # Autostart Tripmaster' /etc/rc.local
    sudo sed -i '/exit 0/i cd \/home\/pi\/tripmaster' /etc/rc.local
    # Startet das Skript im Hintergrund, leitet stdout sowie stderr in eine Datei um und schreibt seine eigene Prozess-ID in die Datei run.pid
    # sudo sed -i '/exit 0/i \/bin\/sleep 5 && sudo .\/tripmaster_web.py > .\/out\/tripmaster.out 2>&1 & echo $! > .\/run.pid' /etc/rc.local
    sudo sed -i '/exit 0/i sudo .\/tripmaster_web.py > .\/out\/tripmaster.out 2>&1 & echo $! > .\/run.pid' /etc/rc.local
    # Damit kann ein im Hintergrund gestarteter Tripmaster mit dem Befehl
    # sudo kill -SIGINT $(cat run.pid)
    # gestoppt werden
    
    # Stromsparoption: HDMI ausschalten
    sudo sed -i '/exit 0/i # Energiesparoption: HDMI ausschalten' /etc/rc.local    
    sudo sed -i '/exit 0/i /usr/bin/tvservice -o\n' /etc/rc.local    
    
    # Das erste Vorkommen von 'exit 0' wieder zurück umbenennen
    sudo sed -i 's/\"exit_0\"/\"exit 0\"/g' /etc/rc.local
    
}


######################################################################
# kernel config
######################################################################
#nohz=off intel_idle.max_cstate=0
#
### PPS (default in Raspberry Pi OS)
#CONFIG_PPS=y
#CONFIG_PPS_CLIENT_LDISC=y
#CONFIG_PPS_CLIENT_GPIO=y
#CONFIG_GPIO_SYSFS=y
#
### PTP (optional addition)
#CONFIG_DP83640_PHY=y
#CONFIG_PTP_1588_CLOCK_PCH=y
#
### KPPS + tuning (optional addition)
#CONFIG_NTP_PPS=y
#CONFIG_PREEMPT_NONE=y
## CONFIG_PREEMPT_VOLUNTARY is not set
## CONFIG_NO_HZ is not set
## CONFIG_HZ_100 is not set
#CONFIG_HZ_1000=y
#CONFIG_HZ=1000
######################################################################

######################################################################
## test commands
######################################################################
#dmesg | grep pps
#sudo ppstest /dev/pps*
#sudo ppswatch -a /dev/pps0
#
#sudo gpsd -D 5 -N -n /dev/ttyAMA0 /dev/pps0 -F /var/run/gpsd.sock
#sudo systemctl stop gpsd.*
#sudo killall -9 gpsd
#sudo dpkg-reconfigure -plow gpsd
#minicom -b 9600 -o -D /dev/ttyAMA0
#cgps
#xgps
#gpsmon
#ipcs -m
#ntpshmmon
#
#sudo systemctl stop gpsd.* && sudo systemctl restart chrony && sudo systemctl start gpsd && echo Done.
#
#chronyc sources
#chronyc sourcestats
#chronyc tracking
#watch -n 10 -p sudo chronyc -m tracking sources sourcestats clients;
######################################################################


handle_update

handle_gps
handle_pps

install_chrony
setup_chrony

# MRO Tripmaster Installationen
install_tripmaster


######################################################################
echo -e "\e[32mDone.\e[0m";
echo -e "\e[1;31mPlease reboot\e[0m";
