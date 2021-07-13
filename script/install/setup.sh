#!/bin/bash

# Passwort des Nutzers pi ändern
echo -e "\e[32mchpasswd\e[0m";
sudo echo 'pi:mjhbuiv71' | sudo chpasswd

# Hostnamen ändern
echo -e "\e[32mhostname\e[0m";
hostname=tripmaster
sudo raspi-config nonint do_hostname $hostname

# Locale, Tastaturlayout und Zeitzone einstellen
echo -e "\e[32mlocale, keyboard, timezone\e[0m";
locale=de_DE.UTF-8
layout=de
timezone=Europe/Berlin
sudo raspi-config nonint do_change_locale $locale
sudo raspi-config nonint do_configure_keyboard $layout
sudo timedatectl set-timezone $timezone

# VNC aktivieren (nur bei OS mit Desktop aktivieren!)
# echo -e "\e[32mVNC\e[0m";
# sudo raspi-config nonint do_vnc 0
