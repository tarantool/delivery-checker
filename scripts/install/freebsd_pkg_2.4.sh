#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

pkg install -y tarantool
sysrc tarantool_enable=YES
sysrc tarantool_instances=/usr/local/etc/tarantool/instances.enabled
