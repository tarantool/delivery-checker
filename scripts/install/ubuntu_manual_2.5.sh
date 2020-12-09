#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

apt-get -y install sudo
sudo apt-get -y install gnupg2
sudo apt-get -y install curl
curl https://download.tarantool.org/tarantool/release/2.5/gpgkey | sudo apt-key add -
sudo apt-get -y install lsb-release
release=`lsb_release -c -s`
sudo apt-get -y install apt-transport-https
sudo rm -f /etc/apt/sources.list.d/*tarantool*.list
echo "deb https://download.tarantool.org/tarantool/release/2.5/ubuntu/ ${release} main" | sudo tee /etc/apt/sources.list.d/tarantool_2_5.list
echo "deb-src https://download.tarantool.org/tarantool/release/2.5/ubuntu/ ${release} main" | sudo tee -a /etc/apt/sources.list.d/tarantool_2_5.list
sudo apt-get -y update
sudo apt-get -y install tarantool
