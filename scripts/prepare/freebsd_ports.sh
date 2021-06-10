#!/bin/sh

# Exit when any command in script file fails
set -ex

# Preparation commands

# Update ports
portsnap fetch update

# Download dependencies to cache it
cd /usr/ports/databases/tarantool
make configure BATCH=yes

# Shutdown VM to indicate that preparation is finished
shutdown -p now
