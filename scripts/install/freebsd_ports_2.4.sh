#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

cd /usr/ports/databases/tarantool
make config-recursive
make install clean
sysrc tarantool_enable=YES
sysrc tarantool_instances=/usr/local/etc/tarantool/instances.enabled
