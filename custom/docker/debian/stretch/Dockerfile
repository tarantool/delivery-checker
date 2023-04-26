FROM debian:stretch

# The support for Debian Stretch ended on June 30, 2022.
# The package repository has been moved to http://archive.debian.org.
ADD sources.list /etc/apt/
RUN echo "Acquire::Check-Valid-Until false;" > /etc/apt/apt.conf.d/00nocheckvalid
