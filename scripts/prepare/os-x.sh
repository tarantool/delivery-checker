#!/bin/sh

# Exit when any command in script file fails
set -ex

# Download dependencies to cache it
brew install --only-dependencies tarantool
brew install --only-dependencies tarantool --HEAD
