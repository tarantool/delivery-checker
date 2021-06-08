#!/bin/sh

# Exit when any command in script file fails
set -ex

# Preparation commands

portsnap fetch
portsnap extract
shutdown -p now
