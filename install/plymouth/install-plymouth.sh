#!/bin/bash

set -e

echo "Installing JCBVFD Plymouth theme..."

sudo mkdir -p /usr/share/plymouth/themes/jcbvfd

sudo cp splash.png /usr/share/plymouth/themes/jcbvfd/
sudo cp jcbvfd.script /usr/share/plymouth/themes/jcbvfd/
sudo cp jcbvfd.plymouth /usr/share/plymouth/themes/jcbvfd/

sudo plymouth-set-default-theme jcbvfd
sudo update-initramfs -u

echo
echo "Installation complete."
echo "Reboot to see the new splash screen."
