#!/bin/sh

# Exit when any command in script file fails
set -ex

# Preparation commands

# Download dependencies to cache it
brew install --only-dependencies tarantool
brew install --only-dependencies tarantool --HEAD

# Shutdown VM to indicate that preparation is finished
sudo shutdown -h now || true
