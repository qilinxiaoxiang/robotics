#!/bin/bash
# Install 90-duck-console-quiet.conf on the A7Z and apply it now (run on the A7Z from this folder).
# Undo: sudo rm /etc/sysctl.d/90-duck-console-quiet.conf && sudo sysctl -w kernel.printk="4 4 1 7"
set -e
cd "$(dirname "$0")"
sudo install -m 644 90-duck-console-quiet.conf /etc/sysctl.d/90-duck-console-quiet.conf
sudo sysctl -p /etc/sysctl.d/90-duck-console-quiet.conf
echo "console loglevel now: $(cat /proc/sys/kernel/printk)"
