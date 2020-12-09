#!/bin/sh

# Exit when any command in script file fails
set -e

# Preparation commands

## On OS install select:
## - distributes: ports
## - startup: sshd, ntpdate, ntpd, dumpdev
## - root password: toor

## After OS install:
#vi /etc/ssh/sshd_config
## PermitRootLogin yes
#chsh -s /bin/sh

shutdown -p now
