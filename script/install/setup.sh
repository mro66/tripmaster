#!/bin/bash

# Passwort des Nutzers pi ändern
echo -e "\e[32mchpasswd\e[0m";
sudo echo 'pi:mjhbuiv71' | sudo chpasswd

# Hostnamen ändern
echo -e "\e[32mhostname\e[0m";
hostname=tripmaster
sudo raspi-config nonint do_hostname $hostname

# Locale, Tastaturlayout und Zeitzone einstellen
locale=de_DE.UTF-8
layout=de
timezone=Europe/Berlin
echo -e "\e[32mlocale\e[0m";
sudo raspi-config nonint do_change_locale $locale
echo -e "\e[32mkeyboard\e[0m";
sudo raspi-config nonint do_configure_keyboard $layout
echo -e "\e[32mtimezone\e[0m";
sudo timedatectl set-timezone $timezone

# VNC aktivieren (nur bei OS mit Desktop aktivieren!)
# echo -e "\e[32mVNC\e[0m";
# sudo raspi-config nonint do_vnc 0
