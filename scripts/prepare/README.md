# Preparing virtual machines

Here you can find commands for virtual machines preparation.

Table of contents:
- [macOS](#macos)
- [FreeBSD](#freebsd)

## macOS

Open VirtualBox application and make some actions:

1. Create a virtual machine, select `Mac OS X (64-bit)` type,
   set hard drive size to 64 GB;
2. Go to "System", disable floppy, select RAM, CPU;
3. Go to "Display", select Video Memory, enable 3D Acceleration;
4. Go to "Network", open "Port Forwarding",
   make routes for `SSH` (port: `22`) and `Tarantool` (port: `3301`).

Set VMs parameters using the following commands:

```shell
export MAC_OS_VM_NAME="mac-os_11.0"

VBoxManage modifyvm "${MAC_OS_VM_NAME}" --cpuidset 00000001 000106e5 00100800 0098e3fd bfebfbff
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal/Devices/efi/0/Config/DmiSystemProduct" "iMac11,3"
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal/Devices/efi/0/Config/DmiSystemVersion" "1.0"
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal/Devices/efi/0/Config/DmiBoardProduct" "Iloveapple"
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal/Devices/smc/0/Config/DeviceKey" "ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc"
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal/Devices/smc/0/Config/GetKeyFromRealSMC" 1
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal2/EfiHorizontalResolution" 1440
VBoxManage setextradata "${MAC_OS_VM_NAME}" "VBoxInternal2/EfiVerticalResolution" 900
VBoxManage setextradata "${MAC_OS_VM_NAME}" "GUI/Fullscreen" true
VBoxManage setextradata "${MAC_OS_VM_NAME}" "GUI/ScaleFactor" 2
```

Download macOS by App Store:
- [macOS Mojave 10.14](https://apps.apple.com/us/app/macos-mojave/id1398502828)
- [macOS Catalina 10.15](https://apps.apple.com/us/app/macos-catalina/id1466841314)
- [macOS Big Sure 11.0](https://apps.apple.com/us/app/macos-big-sur/id1526878132)

Create ISO:

```shell
export MAC_OS_NAME="Big Sur"

export MAC_OS_SIZE="$(du -sm "/Applications/Install macOS ${MAC_OS_NAME}.app/" | cut -f1)"
hdiutil create -o "/tmp/${MAC_OS_NAME}" -size "$(expr ${MAC_OS_SIZE} '*' 11 '/' 10)m" -volname "${MAC_OS_NAME}" -layout SPUD -fs HFS+J
hdiutil attach "/tmp/${MAC_OS_NAME}.dmg" -noverify -mountpoint "/Volumes/${MAC_OS_NAME}"
sudo "/Applications/Install macOS ${MAC_OS_NAME}.app/Contents/Resources/createinstallmedia" --volume "/Volumes/${MAC_OS_NAME}" --nointeraction
hdiutil detach -force "/Volumes/Install macOS ${MAC_OS_NAME}"
hdiutil convert "/tmp/${MAC_OS_NAME}.dmg" -format UDTO -o "${HOME}/Desktop/${MAC_OS_NAME}.cdr"
rm -f "/tmp/${MAC_OS_NAME}.dmg"
mv "${HOME}/Desktop/${MAC_OS_NAME}.cdr" "${HOME}/Desktop/${MAC_OS_NAME}.iso"
```

Next, you should install the OS, connect to VM and make some actions:

1. go to "Software Update", disable automatic updates, install last updates;
2. install guest additions;
3. go to "Sharing" and enable remote login;
4. go to "Security & Privacy" and enable automatic login, disable screen lock;
5. go to "Screen Saver" and disable it;
6. go to "Energy Saver" and disable all sleeps;
7. open shell and execute this commands:

```shell
# Add NOPASSWD option for root user and admin group like here:
# root ALL=(ALL) NOPASSWD: ALL
# %admin ALL=(ALL) NOPASSWD: ALL
sudo visudo

# Add paths to PATH
cat <<EOF >> .bashrc
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin
EOF

# Install xcode
git --version

# Check JDK installation (and install if necessary)
java --version

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
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
