#!/bin/sh

# Exit when any command in script file fails
set -ex

# Preparation commands

# To download and execute tarantool install script
apt-get -y update
apt-get -y upgrade
apt-get -y install curl sudo
