#!/bin/sh

# Exit when any command in script file fails
set -e

# Preparation commands

## Before OS install:
#VBoxManage modifyvm "os-x_10.12_base" --cpuidset 00000001 000106e5 00100800 0098e3fd bfebfbff
#VBoxManage setextradata "os-x_10.12_base" "VBoxInternal/Devices/efi/0/Config/DmiSystemProduct" "iMac11,3"
#VBoxManage setextradata "os-x_10.12_base" "VBoxInternal/Devices/efi/0/Config/DmiSystemVersion" "1.0"
#VBoxManage setextradata "os-x_10.12_base" "VBoxInternal/Devices/efi/0/Config/DmiBoardProduct" "Iloveapple"
#VBoxManage setextradata "os-x_10.12_base" "VBoxInternal/Devices/smc/0/Config/DeviceKey" "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
#VBoxManage setextradata "os-x_10.12_base" "VBoxInternal/Devices/smc/0/Config/GetKeyFromRealSMC" 1
## After OS install:
#sudo visudo
## root ALL=(ALL) NOPASSWD: ALL
## %admin ALL=(ALL) NOPASSWD: ALL
#sudo su
#passwd
## toor
## Go to security settings and remove password
## Go to sharing settings and enable remote login
#/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
#cat <<EOF >> .bashrc
#export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
#EOF
