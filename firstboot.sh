#!/bin/bash

# This script located in /boot directory of the system (or SD card root)
# The name `firstboot.sh` is deliberate to be used with the nmcclain/raspberian-firstboot project

set +e

echo "Enabling dwc2 USB driver..."
echo "dtoverlay=dwc2" | tee -a /boot/config.txt

echo "Enabling dwc2 kernel module..."
echo "dwc2" | tee -a /etc/modules

echo "Creating 8GB backing storage for the USB Gadget..."
truncate -s 8GB /storage.bin
mkfs.vfat /storage.bin -n PSBerry
sync

if [ -f /etc/rc.local ]; then
	echo "`/etc/rc.local` file found - backing up as `/etc/rc.local.bak` for safekeeping..."
	mv /etc/rc.local /etc/rc.local.bak
fi

# enabling g_mass_storage in `/etc/modules` is too early
echo "Enabling g_mass_storage kernel module in `/etc/rc.local`..."
echo "#!/bin/sh -e" | tee -a /etc/rc.local
echo "sudo modprobe g_mass_storage file=/storage.bin removable=1 ro=0 stall=0" | tee -a /etc/rc.local
echo "exit 0" | tee -a /etc/rc.local
chmod +x /etc/rc.local

echo "Installation complete, rebooting in 5 seconds..."
systemd-run --no-block sh -c "sleep 5 && reboot"
exit 0