# Preparing virtual machines

Here you can find commands for virtual machines preparation.

Table of contents:
- [OS X](#OS-X)
- [FreeBSD](#FreeBSD)

## OS X

First, you should create a virtual machine and set its parameters using the
following commands:

```shell
export OS_X_VM_NAME="os-x_10.14"

VBoxManage modifyvm "${OS_X_VM_NAME}" --cpuidset 00000001 000106e5 00100800 0098e3fd bfebfbff
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal/Devices/efi/0/Config/DmiSystemProduct" "iMac11,3"
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal/Devices/efi/0/Config/DmiSystemVersion" "1.0"
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal/Devices/efi/0/Config/DmiBoardProduct" "Iloveapple"
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal/Devices/smc/0/Config/DeviceKey" "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal/Devices/smc/0/Config/GetKeyFromRealSMC" 1
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal2/EfiHorizontalResolution" 1440
VBoxManage setextradata "${OS_X_VM_NAME}" "VBoxInternal2/EfiVerticalResolution" 900
```

Next, you should install the OS, connect to VM and make some actions:

1. go to sharing settings and enable remote login;
2. go to security settings and enable automatic login, disable screen lock;
3. go to screen saver and disable it;
4. go to energy saver and disable all sleeps;
5. open shell and exec this commands:

```shell
# Install xcode
git --version

# Check JDK installation (and install if necessary)
java --version

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

# Add paths to PATH
cat <<EOF >> .bashrc
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
EOF

# Add NOPASSWD option for root user and admin group like here:
# root ALL=(ALL) NOPASSWD: ALL
# %admin ALL=(ALL) NOPASSWD: ALL
sudo visudo
```

## FreeBSD

First, you should create a virtual machine. Next, you should install the OS,
choosing this options:

- distributes: ports;
- startup: sshd, ntpdate, ntpd, dumpdev;
- root password: toor.

After OS install, connect to VM and make some actions:

```shell
# Add/uncomment "PermitRootLogin yes" line in SSH config
vi /etc/ssh/sshd_config

# Change default shell
chsh -s /bin/sh

# Download and extract ports
portsnap fetch extract

# It is also better to manually build the dependencies
# so that you do not get a timeout error at the prepare stage
cd /usr/ports/databases/tarantool
make configure BATCH=yes
```
