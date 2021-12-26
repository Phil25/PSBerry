#!/bin/bash

# This script located in /boot directory of the system (or SD card root)
# The name `firstboot.sh` is deliberate to be used with the nmcclain/raspberian-firstboot project

set +e

echo "Enabling dwc2 USB driver..."
echo "dtoverlay=dwc2" | tee -a /boot/config.txt

echo "Enabling dwc2 kernel module..."
echo "dwc2" | tee -a /etc/modules

echo "Installing exfat formatting utility, pip and image compression library..."
apt install -y exfat-utils pip libopenjp2-7

echo "Creating backing storage with 90% the size of free space..."
FREE_BYTES=$(df -P -B1 / | tail -1 | awk '{print $4}')
truncate -s $(($FREE_BYTES * 9 / 10)) /home/pi/storage.bin
mkfs.exfat -n PSBerry /home/pi/storage.bin
sync

echo "Setting up PSBerry in `/home/pi`..."
mv /boot/PSBerry /home/pi/PSBerry
mkdir /home/pi/mount
sudo python -m pip install -r /home/pi/PSBerry/requirements.txt

if [ -f /etc/rc.local ]; then
	echo "`/etc/rc.local` file found - backing up as `/etc/rc.local.bak` for safekeeping..."
	mv /etc/rc.local /etc/rc.local.bak
fi

echo "Enabling g_mass_storage kernel module in `/etc/rc.local`..." # `/etc/modules` is too early
cat > /etc/rc.local << EOF
#!/bin/sh -e
sudo modprobe g_mass_storage file=/home/pi/storage.bin removable=1 ro=0 stall=0
exit 0
EOF
chmod +x /etc/rc.local

echo "Creating PSBerry systemd service..."
cat > /lib/systemd/system/psberry.service << EOF
[Unit]
Description=PSBerry Service
After=multi-user.target

[Service]
Type=idle
ExecStart=sudo python /home/pi/PSBerry/src/psberry.py --block /home/pi/storage.bin --mount /home/pi/mount

[Install]
WantedBy=multi-user.target
EOF
chmod 644 /lib/systemd/system/psberry.service
systemctl daemon-reload
systemctl enable psberry.service

echo "Installation complete, rebooting in 5 seconds..."
systemd-run --no-block sh -c "sleep 5 && reboot"
exit 0