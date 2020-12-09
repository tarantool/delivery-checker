#!/bin/sh

# Exit when any command in script file fails
set -e

# Preparation commands

## Before OS install:
#VBoxManage modifyvm "os-x_10.13" --cpuidset 00000001 000106e5 00100800 0098e3fd bfebfbff
#VBoxManage setextradata "os-x_10.13" "VBoxInternal/Devices/efi/0/Config/DmiSystemProduct" "iMac11,3"
#VBoxManage setextradata "os-x_10.13" "VBoxInternal/Devices/efi/0/Config/DmiSystemVersion" "1.0"
#VBoxManage setextradata "os-x_10.13" "VBoxInternal/Devices/efi/0/Config/DmiBoardProduct" "Iloveapple"
#VBoxManage setextradata "os-x_10.13" "VBoxInternal/Devices/smc/0/Config/DeviceKey" "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
#VBoxManage setextradata "os-x_10.13" "VBoxInternal/Devices/smc/0/Config/GetKeyFromRealSMC" 1
#VBoxManage setextradata "os-x_10.13" VBoxInternal2/EfiHorizontalResolution 1440
#VBoxManage setextradata "os-x_10.13" VBoxInternal2/EfiVerticalResolution 900

## After OS install:
## Go to sharing settings and enable remote login
## Go to security settings and enable automatic login, disable screen lock
## Go to screen saver and disable it
## Go to energy saver and disable all sleeps
#git --version # to install xcode
#java --version # to check JDK installation (and install if neccessary)
#/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
#cat <<EOF >> .bashrc
#export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
#EOF
#sudo visudo
## root ALL=(ALL) NOPASSWD: ALL
## %admin ALL=(ALL) NOPASSWD: ALL

brew install --only-dependencies tarantool
brew install --only-dependencies tarantool --HEAD
sudo shutdown -h now || true
