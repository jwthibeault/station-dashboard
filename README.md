# James City Bruton Volunteer Fire Department
# Station Dashboard

**Current Version: V2.2.0**

---

## Overview

The Station Dashboard is a Raspberry Pi appliance that continuously displays operational information for the James City Bruton Volunteer Fire Department.

The production dashboard uses a four-window Chromium architecture:

- **BloomWX** — Weather dashboard
- **VDOT** — Virginia Department of Transportation camera wall
- **IamResponding** — Fire/EMS incident dashboard
- **PulsePoint** — Emergency incident dashboard

The dashboard is designed to operate unattended 24 hours a day.

V2.2.0 is the current production release.

---

# V2 Architecture

V2 replaces the original single-dashboard/tab-rotation architecture with four independent Chromium windows.

```text
                         Raspberry Pi
                              |
                              v
                    Debian / labwc desktop
                              |
                              v
                systemd: station-dashboard.service
                              |
                              v
             scripts/start-dashboard-v2.sh
                              |
                              v
                    v2/start-dashboard.py
                         V2 Supervisor
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
       Wrapper Server    Chromium Windows   Network
           :8082          CDP :9230-9233     Monitor
                              |
        +-------------+-------+-------+-------------+
        |             |               |             |
        v             v               v             v
      BloomWX        VDOT       IamResponding   PulsePoint
      CDP 9230      CDP 9231       CDP 9232       CDP 9233
        |             |               |             |
        +-------------+---------------+-------------+
                              |
                              v
                    Health Monitoring
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
           Individual Site          Network-Wide
              Recovery                Recovery
```

Each dashboard has its own Chromium process, browser profile, CDP endpoint, and Playwright connection.

The V2 supervisor manages initialization, health monitoring, network monitoring, and recovery.

---

# Dashboard Configuration

| Dashboard | Local Wrapper URL | Chromium Profile | CDP Port |
|---|---|---|---:|
| BloomWX | `/bloomwx.html` | `/tmp/v2-bloomwx-profile` | 9230 |
| VDOT | `/vdot.html` | `/tmp/v2-vdot-profile` | 9231 |
| IamResponding | `/iamresponding.html` | `/tmp/v2-iamresponding-profile` | 9232 |
| PulsePoint | `/pulsepoint.html` | `/tmp/v2-pulsepoint-profile` | 9233 |

The local wrapper server runs on:

```text
127.0.0.1:8082
```

The wrapper provides the local HTML entry points used by the Chromium windows.

---

# Startup Sequence

The production dashboard is started by systemd.

```text
Power Applied
      |
      v
Debian / labwc
      |
      v
station-dashboard.service
      |
      v
scripts/start-dashboard-v2.sh
      |
      v
v2/start-dashboard.py
      |
      v
Local wrapper server :8082
      |
      v
Chromium Window 1 -- BloomWX  -- CDP 9230
      |
      v
Chromium Window 2 -- VDOT    -- CDP 9231
      |
      v
Chromium Window 3 -- IaR     -- CDP 9232
      |
      v
Chromium Window 4 -- PulsePoint -- CDP 9233
      |
      v
Concurrent dashboard initialization
      |
      v
Continuous health and network monitoring
```

V2 starts the local wrapper server first and waits for it to become available.

The four Chromium windows are then started independently.

Each CDP endpoint is checked independently before dashboard initialization begins.

---

# Chromium Windows

Chromium windows are started by:

```text
scripts/start-v2-window.sh
```

Each window receives:

```text
URL
Profile directory
CDP port
```

Chromium is launched with:

- A dedicated user-data directory
- Remote debugging enabled
- No first-run dialog
- Session-crash dialogs disabled
- Session restoration disabled
- 1920x1080 window size
- Application mode

The four dedicated profiles prevent login/session state from being shared between dashboards.

---

# Dashboard Initialization

V2 initializes all dashboards concurrently using separate Python threads.

Each dashboard has its own Playwright connection to its Chromium CDP endpoint.

Initialization results are recorded independently.

If a dashboard fails during initialization, V2 does not prevent the other dashboards from starting.

The failed dashboard remains under health monitoring and is displayed as down until recovery succeeds.

---

# Health Monitoring

V2 performs continuous health checks every:

```text
30 seconds
```

The health monitors operate independently for each dashboard.

The monitored dashboards currently include:

- BloomWX
- VDOT
- IamResponding

PulsePoint currently has placeholder-only monitoring and remains displayed as an independent Chromium window.

If a monitored dashboard fails its health check, V2 can display the local dashboard-down page and attempt recovery.

---

# Dashboard Recovery

Individual website failures are handled independently when the station network is available.

Recovery may include:

1. Detecting a failed health check.
2. Displaying the dashboard-down page.
3. Reloading or reopening the dashboard.
4. Allowing a 30-second recovery grace period.
5. Performing another health check.
6. Returning to normal monitoring after successful recovery.

The last successful health-check time is maintained for each dashboard.

---

# BloomWX Stale Data Detection

BloomWX has additional health validation.

The BloomWX health monitor detects the site's:

```text
Data not refreshing
```

stale-data condition.

When detected, the BloomWX health check fails and the normal recovery process is initiated.

This prevents a browser page that is still visually loaded but no longer receiving current weather data from being considered healthy.

---

# IamResponding Monitoring

IamResponding is independently monitored through its own Chromium/CDP connection.

The V2 architecture allows IamResponding to recover independently from other dashboards.

Network-wide recovery also reloads the IamResponding dashboard after connectivity is restored.

---

# Network Monitoring

V2 includes a separate network health monitor.

Network checks run every:

```text
5 seconds
```

The network monitor checks both:

- The local network gateway
- An external Internet target

The default external target is:

```text
1.1.1.1
```

Network availability requires:

- Zero packet loss to the local gateway
- No more than 25% packet loss to the external target

The network monitor requires two consecutive failed checks before declaring a network outage.

It requires two consecutive successful checks before declaring the network restored.

---

# Network-Wide Outage Handling

When a network outage is confirmed:

```text
NETWORK OUTAGE CONFIRMED
```

all dashboard monitors stop attempting individual website recovery.

The dashboards instead use the local dashboard-down page to display the network outage condition.

This prevents the individual dashboard monitors from repeatedly attempting website recovery while the station itself has no network connectivity.

The dashboard-down page identifies:

- Network outage status
- Gateway address
- Gateway packet loss
- External test target
- External packet loss
- Last successful dashboard health check

---

# Network Recovery

When the network is restored, the network monitor generates a shared restoration event.

All dashboard monitors observe the same restoration event.

Each dashboard then:

1. Reloads its page.
2. Waits 30 seconds.
3. Performs a health check.
4. Records the successful recovery.
5. Returns to normal monitoring.

This provides coordinated recovery of all dashboards after a station-wide network outage.

---

# Automatic Reboot Protection

If a confirmed network outage remains active for more than:

```text
1 hour
```

V2 automatically requests a Raspberry Pi reboot.

This provides a final recovery mechanism for a prolonged network condition that does not recover normally.

---

# Dashboard Down Page

The local dashboard-down page is:

```text
v2/windows/dashboard-down.html
```

It can display either:

```text
<Dashboard> WEBSITE DOWN
```

or:

```text
<Dashboard> NETWORK OUTAGE
```

The network-outage version provides additional network diagnostic information.

The page is hosted locally by the V2 wrapper server and therefore remains available even when the external Internet connection is unavailable.

---

# Production Systemd Service

The production dashboard is managed by:

```text
station-dashboard.service
```

The service:

- Runs as user `station1`
- Uses `/home/station1/station-dashboard` as its working directory
- Uses the Python virtual environment
- Starts after the graphical and network-online targets
- Automatically restarts if the dashboard process exits

The production service launches:

```text
scripts/start-dashboard-v2.sh
```

which executes:

```text
v2/start-dashboard.py
```

---

# Dashboard Control Utility

The primary maintenance utility is:

```text
tools/dashboardctl
```

Display the current production status:

```bash
./tools/dashboardctl status
```

Display V2 runtime status:

```bash
./tools/dashboardctl v2-status
```

Stop the V2 dashboard:

```bash
./tools/dashboardctl v2-stop
```

Start V2 manually:

```bash
./tools/dashboardctl v2-start
```

Restart V2 manually:

```bash
./tools/dashboardctl v2-restart
```

Restart the production systemd service:

```bash
./tools/dashboardctl restart
```

Display the installed dashboard version:

```bash
./tools/dashboardctl version
```

---

# Useful Systemd Commands

Check service status:

```bash
systemctl status station-dashboard.service
```

Start the production dashboard:

```bash
sudo systemctl start station-dashboard.service
```

Stop the production dashboard:

```bash
sudo systemctl stop station-dashboard.service
```

Restart the production dashboard:

```bash
sudo systemctl restart station-dashboard.service
```

View the service journal:

```bash
journalctl -u station-dashboard.service -f
```

---

# Logs

V2 startup and monitoring output is written to:

```text
/tmp/v2-start-dashboard.log
```

Individual Chromium launch logs are stored in:

```text
/tmp/v2-bloomwx-launch.log
/tmp/v2-vdot-launch.log
/tmp/v2-iamresponding-launch.log
```

The Chromium browser profiles are stored in:

```text
/tmp/v2-bloomwx-profile
/tmp/v2-vdot-profile
/tmp/v2-iamresponding-profile
/tmp/v2-pulsepoint-profile
```

These profile directories are actively used by the running dashboard and should not be manually deleted while V2 is operating.

---

# Important Files

## V2 Supervisor

```text
v2/start-dashboard.py
```

Central V2 process responsible for:

- Wrapper server startup
- Chromium window startup
- CDP readiness checks
- Concurrent dashboard initialization
- Health monitoring
- Network monitoring
- Individual recovery
- Network-wide recovery
- Automatic reboot protection

## Dashboard Modules

```text
station_dashboard/bloomwx.py
station_dashboard/iamresponding.py
station_dashboard/vdot.py
```

## Local Dashboard Windows

```text
v2/windows/bloomwx.html
v2/windows/vdot.html
v2/windows/iamresponding.html
v2/windows/pulsepoint.html
v2/windows/dashboard-down.html
```

## Production Startup

```text
scripts/start-dashboard-v2.sh
```

## Chromium Startup

```text
scripts/start-v2-window.sh
```

## Maintenance Utility

```text
tools/dashboardctl
```

## Systemd Service

```text
station-dashboard.service
```

---

# Project Structure

```text
station-dashboard/
│
├── v2/
│   ├── start-dashboard.py
│   ├── start-bloomwx.py
│   ├── start-iamresponding.py
│   ├── start-vdot.py
│   └── windows/
│       ├── bloomwx.html
│       ├── dashboard-down.html
│       ├── iamresponding.html
│       ├── pulsepoint.html
│       └── vdot.html
│
├── station_dashboard/
│   ├── bloomwx.py
│   ├── browser.py
│   ├── config.py
│   ├── iamresponding.py
│   ├── main.py
│   └── vdot.py
│
├── scripts/
│   ├── start-browser.sh
│   ├── start-dashboard.sh
│   ├── start-dashboard-v2.sh
│   └── start-v2-window.sh
│
├── tools/
│   └── dashboardctl
│
├── install/
├── config.json
├── requirements.txt
├── README.md
└── venv/
```

---

# Python Virtual Environment

Activate the virtual environment:

```bash
source ~/station-dashboard/venv/bin/activate
```

Deactivate:

```bash
deactivate
```

---

# Git Repository

The repository uses:

```text
main
```

as the production branch.

The current production release is:

```text
V2.2.0
```

The V2 development branch is:

```text
v2-development
```

The current production commit is:

```text
841d099
```

Release tag:

```text
V2.1.0
```

The V1 production history remains preserved in Git.

The previous V1.5.1 production release is:

```text
4254c91
```

---

# Development and Recovery

The project uses Git version history to provide a reliable recovery path.

Before making significant dashboard changes:

1. Test one change at a time.
2. Verify dashboard operation.
3. Verify health monitoring.
4. Verify recovery behavior.
5. Commit known-good changes.
6. Push production releases to GitHub.

The V2.2.0 release represents the current known-good production baseline.

---

# Hardware

The dashboard runs on a Raspberry Pi appliance using:

- Raspberry Pi
- Raspberry Pi OS (Debian 13 / Trixie)
- labwc Wayland desktop
- Chromium
- Python
- Playwright
- Python virtual environment
- 1920x1080 display output

The system is intended for unattended 24/7 operation.

---

# Current Production Status

**V2.2.0 is the production Station Dashboard.**

The original V1 dashboard is no longer used for normal station operation.

V2 provides:

- Four independent dashboard windows
- Independent Chromium profiles
- Independent CDP connections
- Concurrent startup
- Independent website health monitoring
- Automatic website recovery
- BloomWX stale-data detection
- Station-wide network monitoring
- Coordinated network recovery
- Local network-outage display
- Automatic reboot after prolonged network outage
- systemd-managed automatic startup
- Git-based release and recovery history
