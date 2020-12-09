#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

curl -L https://tarantool.io/live/2.5/installer.sh | bash
sudo yum install tarantool
