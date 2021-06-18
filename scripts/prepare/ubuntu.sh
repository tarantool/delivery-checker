#!/bin/sh

# Exit when any command in script file fails
set -ex

# Preparation commands

# To install tzdata in docker
# https://dev.to/setevoy/docker-configure-tzdata-and-timezone-during-build-20bk
ln -snf "/usr/share/zoneinfo/${TZ}" "/etc/localtime" && echo "${TZ}" >"/etc/timezone"

# To download and execute tarantool install script
apt-get -y update
apt-get -y upgrade
apt-get -y install curl sudo
