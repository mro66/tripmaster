#! /bin/bash

clear

wlan1ip=$(ifconfig | grep -A 1 'wlan1' | tail -1 | cut -d ' ' -f 10)
scriptdir=~/tripmaster/script

if [ -z "$wlan1ip" ]
then
	updownwlan1="Starte"
	ifconfigwlan1="up"
else
	updownwlan1="Stoppe"
	ifconfigwlan1="down"
fi

while [ 1 ]
do
CHOICE=$(
whiptail --title "Tripmaster Steuerung" --menu "Auswahl treffen:" 14 50 7 \
        "1)" "Verfolge Tripmaster LOG" \
        "2)" "Verfolge Tripmaster ERR" \
        "3)" "Stoppe Tripmaster" \
        "4)" "Starte Tripmaster" \
        "5)" "Starte Tripmaster DEBUG" \
	"6)" "Full System Upgrade" \
        "7)" "$updownwlan1 externen WLAN-Adapter"   \
        3>&2 2>&1 1>&3
)

case $CHOICE in
        "1)")
                trap $scriptdir/tripmaster_log.sh EXIT
        ;;
        "2)")
                trap $scriptdir/tripmaster_err.sh EXIT
        ;;
	"3)")
		trap $scriptdir/kill_tripmaster.sh EXIT
	;;
	"4)")
		trap $scriptdir/start_tripmaster.sh EXIT
	;;
	"5)")
		trap $scriptdir/start_tripmaster_debug.sh EXIT
	;;
	"6)")
	         sudo ifconfig wlan1 up
                 while [[ "$wlan1ip" != *"."* ]]
                 do
                         sleep 2
                         wlan1ip=$(ifconfig | grep -A 1 'wlan1' | tail -1 | cut -d ' ' -f 10)
                 done
                 whiptail --msgbox "Der externe WLAN-Adapter\nhat die IP $wlan1ip" 10 40
                 if (whiptail --title "Update" --yesno "Full System Upgrade?" 10 40)
                 then
                         echo "--- UPDATE ---"
                         echo
                         sudo apt update
                         echo
                         echo "--- UPGRADE ---"
                         echo
                         sudo apt -y upgrade
                         echo
                         echo "--- AUTOREMOVE ---"
                         echo
                         sudo apt-get autoremove
                         echo
                fi
		sudo ifconfig wlan1 down
		whiptail --msgbox "Externer WLAN-Adapter gestoppt" 10 40
	;;
        "7)")
                $(sudo ifconfig wlan1 $ifconfigwlan1)
                if [ "$ifconfigwlan1" = "up" ]
                then
                        while [[ "$wlan1ip" != *"."* ]]
                        do
                                sleep 2
                                wlan1ip=$(ifconfig | grep -A 1 'wlan1' | tail -1 | cut -d ' ' -f 10)
                        done
                        whiptail --msgbox "Der externe WLAN-Adapter\nhat die IP $wlan1ip" 10 40
                else
                        whiptail --msgbox "Externer WLAN-Adapter gestoppt" 10 40
                fi
        ;;
esac
exit
done
