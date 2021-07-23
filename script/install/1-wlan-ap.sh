#!/bin/bash

######################################################################
# tested on RPi4B and 2020-05-27-raspios-buster-armhf.zip


##################################################################
BACKUP_FILE=backup.tar.xz
BACKUP_TRANSFORM=s/^/$(date +%Y-%m-%dT%H_%M_%S)-tripmaster\\//

do_backup() {
    tar -ravf "$BACKUP_FILE" --transform="$BACKUP_TRANSFORM" -C / "$1" &>/dev/null
}

setup_system() {
    echo -e "\e[32msetup_system()\e[0m";
    
    # Passwort des Nutzers pi ändern
    echo -e "\e[36m    change password\e[0m";
    sudo echo 'pi:mjhbuiv71' | sudo chpasswd

    # Hostnamen ändern
    echo -e "\e[36m    change hostname\e[0m";
    hostname=tripmaster
    sudo raspi-config nonint do_hostname $hostname

    # Locale, Tastaturlayout und Zeitzone einstellen
    locale=de_DE.UTF-8
    layout=de
    timezone=Europe/Berlin
    echo -e "\e[36m    locale\e[0m";
    sudo raspi-config nonint do_change_locale $locale
    # echo -e "\e[36m    keyboard\e[0m";
    # sudo raspi-config nonint do_configure_keyboard $layout
    echo -e "\e[36m    timezone\e[0m";
    sudo timedatectl set-timezone $timezone

    # VNC aktivieren (nur bei OS mit Desktop aktivieren!)
    # echo -e "\e[36m    VNC\e[0m";
    # sudo raspi-config nonint do_vnc 0
}


######################################################################
handle_update() {
    echo -e "\e[32mhandle_update()\e[0m";

    sudo sync \
    && echo -e "\e[32mupdate...\e[0m" && sudo apt update \
    && echo -e "\e[32mupgrade...\e[0m" && sudo apt full-upgrade -y \
    && echo -e "\e[32mautoremove...\e[0m" && sudo apt autoremove -y --purge \
    && echo -e "\e[32mautoclean...\e[0m" && sudo apt autoclean \
    && echo -e "\e[32mDone.\e[0m" \
    && sudo sync;
}


# ####################################################################
install_wifidriver() {
    # Für meinen speziellen USB-Wifi-Adapter gibt es zurzeit (07/2021) keine direkte Unterstützung durch den Kernel, 
    # so dass ein eigener Treiber installiert werden muss:
    echo -e "\e[32minstall_wifidriver\e[0m";
    
    sudo wget http://downloads.fars-robotics.net/wifi-drivers/install-wifi -O /usr/bin/install-wifi
    
    sudo chmod +x /usr/bin/install-wifi
    
    sudo install-wifi
    
    
}


# ####################################################################
install_accesspoint() {
    echo -e "\e[32minstall_accesspoint\e[0m";

    ##################################################################
    echo -e "\e[36m    install hostapd\e[0m";
    sudo apt install hostapd -y
    sudo systemctl unmask hostapd
    sudo systemctl enable hostapd
    
    ##################################################################
    echo -e "\e[36m    install dnsmasq\e[0m";
    sudo apt install dnsmasq -y
    
    ##################################################################
    echo -e "\e[36m    configure dhcpcd/dnsmasq\e[0m";
    do_backup /etc/dhcpcd.conf
    cat << EOF | sudo tee -a /etc/dhcpcd.conf &>/dev/null

# wlan0 als Tripmaster Access Point
interface wlan0
    static ip_address=19.66.71.1/24
    nohook wpa_supplicant
EOF
    do_backup /etc/dnsmasq.conf
    cat << EOF | sudo tee /etc/dnsmasq.conf &>/dev/null
# Listening interface
interface=wlan0
# Pool of IP addresses served via DHCP
dhcp-range=19.66.71.2,19.66.71.20,255.255.255.0,24h
# Local wireless DNS domain
domain=wlan.tripmaster
# Alias for this router
address=/trip.master/19.66.71.1
# No dhcp for wlan1
no-dhcp-interface=wlan1
EOF
    sudo rfkill unblock wlan
    
    ##################################################################
    echo -e "\e[36m    configure hostapd\e[0m";
    cat << EOF | sudo tee /etc/hostapd/hostapd.conf &>/dev/null
country_code=DE
interface=wlan0
driver=nl80211
ssid=TripmasterAP
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=tripmasterap
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

    ##################################################################
    echo -e "\e[36m    configure routing and NAT\e[0m";
        cat << EOF | sudo tee -a /etc/sysctl.conf &>/dev/null

net.ipv4.ip_forward=1

EOF
    sudo iptables -t nat -A POSTROUTING -o wlan1 -j MASQUERADE
    sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"
    
    # In der *€!$$* rc.local steht _zwei Mal_ exit 0, daher muss das erste Vorkommen (mit "") umbenannt werden
    sudo sed -i 's/\"exit 0\"/\"exit_0\"/g' /etc/rc.local
    # Vor dem zweiten Vorkommen von exit 0 die benötigten Befehle eintragen
    sudo sed -i '/exit 0/i iptables-restore < /etc/iptables.ipv4.nat\n' /etc/rc.local
    # Das erste Vorkommen wieder zurück umbenennen
    sudo sed -i 's/\"exit_0\"/\"exit 0\"/g' /etc/rc.local
    
}


######################################################################

setup_system

# MRO WIFI Treiber installieren
install_wifidriver

# MRO Tripmaster Access Point
install_accesspoint


######################################################################
echo -e "\e[32mDone.\e[0m";
echo -e "\e[1;31mPlease insert WLAN1 and reboot\e[0m";
