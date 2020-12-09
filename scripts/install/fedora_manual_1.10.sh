#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

dnf -y install sudo
sudo rm -f /etc/yum.repos.d/*tarantool*.repo
sudo tee /etc/yum.repos.d/tarantool_1_10.repo <<- EOF
[tarantool_1_10]
name=Fedora-\$releasever - Tarantool
baseurl=https://download.tarantool.org/tarantool/release/1.10/fedora/\$releasever/x86_64/
gpgkey=https://download.tarantool.org/tarantool/release/1.10/gpgkey
repo_gpgcheck=1
gpgcheck=0
enabled=1
[tarantool_1_10-source]
name=Fedora-\$releasever - Tarantool Sources
baseurl=https://download.tarantool.org/tarantool/release/1.10/fedora/\$releasever/SRPMS
gpgkey=https://download.tarantool.org/tarantool/release/1.10/gpgkey
repo_gpgcheck=1
gpgcheck=0
EOF
sudo dnf -q makecache -y --disablerepo='*' --enablerepo='tarantool_1_10'
sudo dnf -y install tarantool
