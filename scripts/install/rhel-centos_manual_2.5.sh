#!/bin/sh

# Exit when any command in script file fails
set -e

# Installation commands

yum clean all
release=$(cat /etc/centos-release | grep -Po "[6-9]" | head -1)
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-$release.noarch.rpm
sed 's/enabled=.*/enabled=1/g' -i /etc/yum.repos.d/epel.repo
rm -f /etc/yum.repos.d/*tarantool*.repo
tee /etc/yum.repos.d/tarantool_2_5.repo <<EOF
[tarantool_2_5]
name=EnterpriseLinux-$release - Tarantool
baseurl=https://download.tarantool.org/tarantool/release/2.5/el/$release/x86_64/
gpgkey=https://download.tarantool.org/tarantool/release/2.5/gpgkey
repo_gpgcheck=1
gpgcheck=0
enabled=1
[tarantool_2_5-source]
name=EnterpriseLinux-$release - Tarantool Sources
baseurl=https://download.tarantool.org/tarantool/release/2.5/el/$release/SRPMS
gpgkey=https://download.tarantool.org/tarantool/release/2.5/gpgkey
repo_gpgcheck=1
gpgcheck=0
EOF
yum makecache -y --disablerepo='*' --enablerepo='tarantool_2_5' --enablerepo='epel'
yum -y install tarantool
