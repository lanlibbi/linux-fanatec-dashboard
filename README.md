# Fanatec Wheelbase Dashboard für Linux

Web-Dashboard zum Tunen von Fanatec-Wheelbases (CSL DD, ClubSport, Podium …) direkt aus dem Browser — auf Basis der `ftec_tuning`-Sysfs-Schnittstelle des Community-Kerneltreibers [hid-fanatecff](https://github.com/gotzl/hid-fanatecff).

Kein FanaLab, kein Windows, keine Abhängigkeiten: **nur Python-Stdlib.**

## Features

- **Lenkwinkel (SEN)** bis 2530° mit Presets (360° / 540° / 720° / 900° / 1080°)
- **FFB-Stärke (FF)**, Dämpfung (DPR), Shock (SHO), Spring (SPR), Force (FOR), Intensität (INT)
- Natural Damping / Friction / Inertia (NDP / NFR / NIN)
- FFS, Auto-Centering Pull (ACP), Brake-Lock-Indicator (BLI), brF, FEI
- **FullForce** und **Advanced Mode** als Schalter
- Tuning-Slot-Wechsel (SLOT) + RESET (fordert die Tuning-Werte neu von der Base an)
- Live-Werte mit Auto-Refresh, Dark-UI, mobiltauglich

## Funktionsweise

Der Treiber [hid-fanatecff](https://github.com/gotzl/hid-fanatecff) legt für kompatible
Wheelbases ein `ftec_tuning`-Gerät unter `/sys/class/ftec_tuning/` an. Die Dateien dort
entsprechen dem Fanatec-Tuning-Menü (SEN, FF, SHO, …). Das Dashboard liest und schreibt
diese Dateien über eine kleine HTTP-API:

- `GET /api/values` → alle aktuellen Tuning-Werte (JSON)
- `POST /api/set` → `{"attr": "FF", "value": 90}` (Whitelist-geschützt, nur bekannte Attribute)

Kein Root nötig: Der Treiber legt die Tuning-Attribute der Gruppe `games` zugänglich an.

> **Wichtig:** Der Treiber blockiert Schreibzugriffe, bis die Tuning-Werte einmal von der
> Base gelesen wurden. Das Dashboard triggert dieses Lesen automatisch (Schreiben in
> `RESET` fordert die Werte an — trotz des Namens kein Werks-Reset).

## Voraussetzungen

- Linux + Python 3 (getestet: Python 3.12, Kernel 7.0)
- [hid-fanatecff](https://github.com/gotzl/hid-fanatecff)-Treiber installiert
- Nutzer in der Gruppe `games` (siehe Treiber-udev-Regel: `sudo usermod -aG games $USER`, danach neu anmelden)
- Wheelbase im **PC-Modus** (CSL DD: rote LED)

## Treiber installieren

Am einfachsten mit dem beigelegten Skript:

```bash
./install-driver.sh
```

Manuell:

```bash
git clone --depth 1 https://github.com/gotzl/hid-fanatecff.git
cd hid-fanatecff
sudo bash ./install.sh --release      # DKMS — überlebt Kernel-Updates
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo modprobe hid_fanatec
# Wheelbase-USB einmal ab-/anstecken
```

Prüfen:

```bash
lsmod | grep fanatec
grep -i -A8 fanatec /proc/bus/input/devices   # „B: FF=…" = Force Feedback aktiv
```

Hinweise:
- **Secure Boot** muss deaktiviert sein (oder das Modul selbst signieren).
- Kernel-Header (`linux-headers-$(uname -r)`) müssen installiert sein.
- Der Treiber unterstützt u. a.: CSL DD (0EB7:0020), CSL DD Pro, ClubSport DD, CSL Elite, Podium DD1/DD2, ClubSport V2/V2.5.

## Dashboard installieren

Manuell:

```bash
python3 fanatec_dashboard.py 8088
# → http://<server-ip>:8088
```

Als systemd-Dienst (Pfade/User in der Unit-Datei anpassen):

```bash
sudo cp fanatec-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fanatec-dashboard
```

## Sicherheit

Das Board hat **keine Authentifizierung**. Es schreibt direkt an die Hardware.
Nur in einem vertrauenswürdigen Netz betreiben (LAN / Tailscale — z. B. per
`--port`-Parameter und Firewall-Regel begrenzen).

## Getestet mit

- Fanatec CSL DD Wheel Base (`0eb7:0020`) + McLaren GT3 V2 Rim + CSL Pedals (über RJ12 an der Base)
- Ubuntu, Python 3.12, Kernel 7.0

## Attribut-Referenz (Fanatec-Tuning-Menü)

| Kürzel | Bedeutung | Bereich |
|--------|-----------|---------|
| SEN | Lenkwinkel | 90–2530° (device-abhängig) |
| FF | FFB-Stärke | 0–100 |
| SHO | Shock | 0–100 |
| DPR | Dämpfung | 0–100 |
| FOR | Force | 0–100 |
| SPR | Spring | 0–100 |
| INT | Intensität | 0–100 |
| NDP / NFR / NIN | Natural Damping / Friction / Inertia | 0–100 |
| FFS | FFB-Sensitivity | 0–100 |
| ACP | Auto-Centering Pull | 0–100 |
| BLI | Brake-Lock-Indicator | 0–101 |
| FUL | FullForce | 0/1 |
| advanced_mode | Advanced Mode | 0/1 |
| SLOT | Aktiver Tuning-Slot | 1–5 |
| RESET | Tuning-Werte neu von der Base lesen (Trigger) | – |

## Credits

- [gotzl/hid-fanatecff](https://github.com/gotzl/hid-fanatecff) — der Treiber, der das alles möglich macht

## Lizenz

[MIT](LICENSE)