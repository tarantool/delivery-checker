#!/bin/sh

# Exit when any command in script file fails
set -ex

# Preparation commands

# Enable vault mirror because Centos 8 is EOL
dist=$(grep -Po "[6-9]" /etc/centos-release | head -1)
if [ $dist = "8" ]; then
    find /etc/yum.repos.d/ -type f -exec sed -i 's/mirrorlist=/#mirrorlist=/g' {} +
    find /etc/yum.repos.d/ -type f -exec sed -i 's/#baseurl=/baseurl=/g' {} +
    find /etc/yum.repos.d/ -type f -exec sed -i 's/mirror.centos.org/vault.centos.org/g' {} +
fi

# To download and execute tarantool install script
yum -y upgrade
yum -y install sudo
