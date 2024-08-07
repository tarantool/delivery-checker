ARG ARCH=
FROM ${ARCH}centos:7

# Set repos URL to archive.kernel.org because CentOS 7 reached EOL and
# original base repos are not available anymore.
RUN sed -i '/mirrorlist/d' /etc/yum.repos.d/* && \
    sed -i -E 's,#[[:space:]]?baseurl=http://mirror.centos.org,baseurl=http://archive.kernel.org,g' /etc/yum.repos.d/* && \
    sed -i 's/$releasever/7.9.2009/g' /etc/yum.repos.d/* && \
    sed -i 's,7/,7.9.2009/,g' /etc/yum.repos.d/* && \
    if [ $(uname -m) = 'aarch64' ]; then \
        sed -i 's,altarch/,centos/altarch/,g' /etc/yum.repos.d/*; \
    fi
