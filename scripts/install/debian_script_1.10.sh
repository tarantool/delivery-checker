#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

curl -L https://tarantool.io/release/1.10/installer.sh | bash
sudo apt-get install tarantool
