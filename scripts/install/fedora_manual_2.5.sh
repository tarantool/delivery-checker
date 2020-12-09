#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

dnf -y install sudo
sudo rm -f /etc/yum.repos.d/*tarantool*.repo
sudo tee /etc/yum.repos.d/tarantool_2_5.repo  <<- EOF
[tarantool_2_5]
name=Fedora-\$releasever - Tarantool
baseurl=https://download.tarantool.org/tarantool/release/2.5/fedora/\$releasever/x86_64/
gpgkey=https://download.tarantool.org/tarantool/release/2.5/gpgkey
repo_gpgcheck=1
gpgcheck=0
enabled=1
[tarantool_2_5-source]
name=Fedora-\$releasever - Tarantool Sources
baseurl=https://download.tarantool.org/tarantool/release/2.5/fedora/\$releasever/SRPMS
gpgkey=https://download.tarantool.org/tarantool/release/2.5/gpgkey
repo_gpgcheck=1
gpgcheck=0
EOF
sudo dnf -q makecache -y --disablerepo='*' --enablerepo='tarantool_2_5'
sudo dnf -y install tarantool
