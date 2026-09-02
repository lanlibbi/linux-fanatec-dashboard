#!/usr/bin/env bash
# Installiert den hid-fanatecff-Kerneltreiber (DKMS) für Fanatec Wheelbases.
# Quelle: https://github.com/gotzl/hid-fanatecff
set -euo pipefail

DEST="$(mktemp -d)/hid-fanatecff"
echo ">> Klone Treiber-Quelle nach $DEST"
git clone --depth 1 https://github.com/gotzl/hid-fanatecff.git "$DEST"
cd "$DEST"

echo ">> Baue Test (ohne Root) — schlägt hier fehl, fehlen Kernel-Header:"
make

echo ">> DKMS-Installation (surviving kernel updates):"
sudo bash ./install.sh --release

echo ">> udev-Regeln neu laden:"
sudo udevadm control --reload-rules && sudo udevadm trigger

echo ">> Modul laden (falls noch nicht geschehen):"
sudo modprobe hid_fanatec || true

echo
echo "Fertig! Jetzt: Wheelbase-USB einmal ab-/anstecken."
echo "Prüfen mit:  lsmod | grep fanatec"
echo "             grep -i -A8 fanatec /proc/bus/input/devices   # B: FF-Zeile = Force Feedback aktiv"