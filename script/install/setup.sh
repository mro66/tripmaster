#!/bin/bash

# Passwort des Nutzers pi ändern
sudo echo 'pi:mjhbuiv71' | sudo chpasswd

# Hostnamen ändern
hostname=tripmaster
sudo raspi-config nonint do_hostname $hostname

# Locale, Tastaturlayout und Zeitzone einstellen
locale=de_DE.UTF-8
layout=de
timezone=Europe/Berlin
sudo raspi-config nonint do_change_locale $locale
sudo raspi-config nonint do_configure_keyboard $layout
sudo timedatectl set-timezone $timezone

# VNC aktivieren (nur bei OS mit Desktop aktivieren!)
# sudo raspi-config nonint do_vnc 0
