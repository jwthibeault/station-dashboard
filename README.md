# James City Bruton Volunteer Fire Department
# Station Dashboard

Version 1.0.0

---

# Overview

The Station Dashboard is a Raspberry Pi appliance that continuously displays operational information for the James City Bruton Volunteer Fire Department.

The system automatically displays:

- IamResponding Dashboard
- Virginia Department of Transportation (VDOT) Camera Wall

The dashboard is designed to operate unattended 24 hours a day.

---

# Features

- Automatic startup after boot
- Chromium launches automatically
- Chromium runs in kiosk mode
- Automatic dashboard rotation
- Health monitoring of both dashboards
- Automatic recovery when either site logs out
- Custom James City Bruton VFD boot splash
- Screen blanking disabled
- Git version history for safe recovery

---

# Hardware

- Raspberry Pi
- Raspberry Pi OS (Debian 13 - Trixie)
- Chromium Browser
- Playwright
- Python Virtual Environment

---

# Project Structure

```
station-dashboard/
│
├── station_dashboard/      Python application
├── scripts/                Startup scripts
├── install/
│   └── plymouth/           Boot splash installation
├── config.json             Configuration
├── requirements.txt
├── README.md
└── venv/
```

---

# Startup Sequence

```
Power Applied
        │
        ▼
JCBVFD Plymouth Splash
        │
        ▼
Debian Desktop (labwc)
        │
        ▼
Chromium Starts
        │
        ▼
Dashboard Service Starts
        │
        ▼
Playwright Connects
        │
        ▼
IamResponding Opens
        │
        ▼
VDOT Opens
        │
        ▼
Dashboard Rotation Begins
```

---

# Dashboard Operation

The dashboard continuously monitors both browser tabs.

If either site logs out:

- The logout is detected automatically.
- The login page is opened.
- Credentials are entered automatically.
- The dashboard resumes operation without user intervention.

---

# Configuration

Application settings are stored in:

```
config.json
```

This includes:

- Login credentials
- Rotation interval
- Dashboard configuration

---

# Important Files

### Main Application

```
station_dashboard/main.py
```

### Browser Management

```
station_dashboard/browser.py
```

### IamResponding

```
station_dashboard/iamresponding.py
```

### VDOT

```
station_dashboard/vdot.py
```

### Chromium Startup

```
scripts/start-browser.sh
```

### Plymouth Boot Splash

```
install/plymouth/
```

---

# System Startup

Two startup mechanisms are intentionally used.

### labwc

Starts Chromium after the graphical desktop is available.

```
~/.config/labwc/autostart
```

This launches:

```
~/station-dashboard/scripts/start-browser.sh
```

### systemd

Starts and monitors the dashboard application.

```
station-dashboard.service
```

Both are required for reliable startup.

---

# Useful Commands

## Stop Dashboard

```bash
sudo systemctl stop station-dashboard.service
```

## Start Dashboard

```bash
sudo systemctl start station-dashboard.service
```

## Restart Dashboard

```bash
sudo systemctl restart station-dashboard.service
```

## Dashboard Status

```bash
sudo systemctl status station-dashboard.service
```

---

# Python Virtual Environment

Activate:

```bash
source ~/station-dashboard/venv/bin/activate
```

Deactivate:

```bash
deactivate
```

---

# Git

## Check Status

```bash
git status
```

## Commit

```bash
git add .
git commit -m "Description"
```

## View History

```bash
git log --oneline
```

## Restore Working Files

```bash
git restore .
```

## Restore Previous Version

```bash
git reset --hard <commit>
```

---

# Plymouth Installation

The custom boot splash is stored in:

```
install/plymouth
```

Install with:

```bash
./install-plymouth.sh
```

---

# Troubleshooting

## Chromium Does Not Start

Verify:

```
~/.config/labwc/autostart
```

contains:

```
~/station-dashboard/scripts/start-browser.sh &
```

---

## Dashboard Does Not Start

Check:

```bash
sudo systemctl status station-dashboard.service
```

---

## Dashboard Stops Rotating

Verify:

- Chromium is running.
- Remote debugging is enabled.
- `config.json` is valid.

---

## Login Recovery

Both IamResponding and VDOT automatically recover from expired login sessions.

No user interaction should normally be required.

---

# Version History

| Version | Description |
|----------|-------------|
| 1.0.0 | Initial production release |
| 0.5.0 | Plymouth boot splash |
| 0.4.0 | Raspberry Pi integration |
| 0.3.0 | Automatic dashboard recovery |
| 0.2.0 | Dashboard health monitoring |
| 0.1.0 | Initial dashboard |

---

# Future Enhancements

Potential future improvements:

- Wayland-compatible mouse cursor hiding
- Weather dashboard
- Additional dashboard pages
- Remote monitoring
- Logging
- Automatic updates

---

Developed for the

**James City Bruton Volunteer Fire Department**

Version 1.0.0
