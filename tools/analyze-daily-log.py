#!/usr/bin/env python3

import re
import subprocess
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict


COMPONENTS = ["PulsePoint", "BloomWX", "IamResponding", "VDOT"]
LOCAL_TZ = ZoneInfo("America/New_York")


# ----------------------------------------------------------------------
# JOURNAL
# ----------------------------------------------------------------------

def journal_lines():
    args = ["journalctl"]

    if len(sys.argv) == 6 and sys.argv[1] == "--period":
        start_arg = datetime.strptime(
            sys.argv[2] + sys.argv[3],
            "%m%d%y%H%M",
        ).replace(tzinfo=LOCAL_TZ)

        end_arg = datetime.strptime(
            sys.argv[4] + sys.argv[5],
            "%m%d%y%H%M",
        ).replace(tzinfo=LOCAL_TZ)

        args += [
            "--since", start_arg.isoformat(),
            "--until", end_arg.isoformat(),
        ]
    else:
        args += ["--since", "24 hours ago"]

    args += [
        "-o", "short-iso",
        "--no-pager",
    ]

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.splitlines()


def parse_ts(line):
    m = re.match(
        r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d)",
        line
    )
    if not m:
        return None
    return datetime.fromisoformat(m.group(1))


def format_time(ts):
    if not ts:
        return "UNKNOWN"
    return ts.strftime("%-I:%M:%S %p")


# ----------------------------------------------------------------------
# BOOT HISTORY
# ----------------------------------------------------------------------

def get_boots():
    """Return actual Pi boots reported by journalctl --list-boots."""

    result = subprocess.run(
        [
            "journalctl",
            "--list-boots",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    boots = []

    for line in result.stdout.splitlines():

        # Example:
        # -1 BOOTID Thu 2026-08-27 15:33:32 EDT Thu 2026-08-27 15:53:01 EDT

        parts = line.split()

        if len(parts) < 10:
            continue

        try:
            idx = int(parts[0])
        except ValueError:
            continue

        boot_id = parts[1]

        try:
            first = datetime.strptime(
                f"{parts[3]} {parts[4]}",
                "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=LOCAL_TZ)

            last = datetime.strptime(
                f"{parts[7]} {parts[8]}",
                "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=LOCAL_TZ)

        except (ValueError, IndexError):
            continue

        boots.append({
            "idx": idx,
            "id": boot_id,
            "first": first,
            "last": last,
        })

    return boots


# ----------------------------------------------------------------------
# NETWORK
# ----------------------------------------------------------------------

def classify_network(line):
    m = re.search(
        r"gateway_loss=([\d.]+)%.*"
        r"external_loss=([\d.]+)%.*"
        r"available=(True|False)",
        line,
    )

    if not m:
        return None

    gateway = float(m.group(1))
    external = float(m.group(2))
    available = m.group(3) == "True"

    if not available:
        return "FAILED", gateway, external

    if gateway > 0 or external > 0:
        return "DEGRADED", gateway, external

    return "HEALTHY", gateway, external


# ----------------------------------------------------------------------
# LOAD JOURNAL
# ----------------------------------------------------------------------

raw_lines = journal_lines()

entries = []

for raw in raw_lines:
    ts = parse_ts(raw)

    if ts:
        entries.append((ts, raw))

if not entries:
    print("No parseable journal entries found.")
    sys.exit(1)

start = entries[0][0]
end = entries[-1][0]

boots = get_boots()

# Restrict boot count to boots overlapping the 24-hour journal period.
boots = [
    boot for boot in boots
    if boot["last"] >= start and boot["first"] <= end
]


# ----------------------------------------------------------------------
# SYSTEM EVENTS
# ----------------------------------------------------------------------

service_starts = 0
service_stops = 0
dashboard_starts = []
pids = []

for ts, line in entries:

    if "Started station-dashboard.service" in line:
        service_starts += 1
        dashboard_starts.append(ts)

    if "Stopped station-dashboard.service" in line:
        service_stops += 1

    m = re.search(r"start-dashboard-v2\.sh\[(\d+)\]", line)

    if m:
        pid = m.group(1)
        if pid not in pids:
            pids.append(pid)


# Match dashboard starts to actual Pi boots.
dashboard_correlations = []

for ts in dashboard_starts:

    matching_boot = None

    for boot in boots:
        delta = ts - boot["first"]

        if timedelta(seconds=0) <= delta <= timedelta(seconds=30):
            matching_boot = boot
            break

    if matching_boot:
        dashboard_correlations.append({
            "dashboard_start": ts,
            "boot": matching_boot,
            "type": "BOOT",
            "delta": ts - matching_boot["first"],
        })
    else:
        dashboard_correlations.append({
            "dashboard_start": ts,
            "boot": None,
            "type": "DASHBOARD",
            "delta": None,
        })


# ----------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------

print()
print("=" * 72)
print("STATION DASHBOARD DAILY EVENT ANALYSIS")
print("=" * 72)
print("SOURCE: systemd journal (journalctl)")
print(
    f"Period: {start:%Y-%m-%d %-I:%M:%S %p} → "
    f"{end:%Y-%m-%d %-I:%M:%S %p}"
)
print()


# ----------------------------------------------------------------------
# SYSTEM
# ----------------------------------------------------------------------

print("SYSTEM")
print(f"  Pi boots detected:             {len(boots)}")
print(f"  Dashboard service starts:     {service_starts}")
print(f"  Dashboard service stops:      {service_stops}")
print(f"  Dashboard process instances:  {len(pids)}")

for i, event in enumerate(dashboard_correlations, 1):

    if event["type"] == "BOOT":
        boot = event["boot"]

        print(
            f"    Dashboard start #{i}: {format_time(event['dashboard_start'])} "
            f"[BOOT #{boot['idx']} {format_time(boot['first'])}, "
            f"{event['delta']}]"
        )

    else:
        print(
            f"    Dashboard start #{i}: {format_time(event['dashboard_start'])} "
            f"[DASHBOARD START — NO BOOT MATCH]"
        )

if pids:
    print(f"  Process IDs: {', '.join(pids)}")

print()


# ----------------------------------------------------------------------
# COMPONENT INCIDENTS
# ----------------------------------------------------------------------

incidents = defaultdict(list)

# Actual dashboard page reloads.
# These are confirmed by the existing journal messages emitted
# after dashboard.open() successfully completes.
page_reloads = {
    component: {
        "health_recovery": 0,
        "network_restoration": 0,
    }
    for component in COMPONENTS
}

for ts, line in entries:

    # A successful health-check recovery calls dashboard.open().
    for component in COMPONENTS:
        if f"{component} recovery navigation completed." in line:
            page_reloads[component]["health_recovery"] += 1

        # A network restoration calls dashboard.open() and then
        # emits "<component>: reload completed."
        if f"{component}: reload completed." in line:
            page_reloads[component]["network_restoration"] += 1


    # PulsePoint
    if "PulsePoint health check FAILED (2 consecutive)." in line:
        unresolved = [
            x for x in incidents["PulsePoint"]
            if x["recovery"] is None
        ]

        if not unresolved:
            incidents["PulsePoint"].append({
                "start": ts,
                "type": "failure",
                "recovery": None,
            })

    elif "PulsePoint recovery PASSED." in line:
        for incident in reversed(incidents["PulsePoint"]):
            if incident["recovery"] is None:
                incident["recovery"] = ts
                break

    # BloomWX
    if "BloomWX initialization FAILED" in line:
        unresolved = [
            x for x in incidents["BloomWX"]
            if x["recovery"] is None
        ]

        if not unresolved:
            incidents["BloomWX"].append({
                "start": ts,
                "type": "initialization failure",
                "recovery": None,
            })

    elif "BloomWX recovery PASSED" in line:
        for incident in reversed(incidents["BloomWX"]):
            if incident["recovery"] is None:
                incident["recovery"] = ts
                break

    # IamResponding / VDOT
    for component in ["IamResponding", "VDOT"]:

        if component not in line:
            continue

        if re.search(
            rf"{component}.*health check FAILED",
            line,
        ):
            unresolved = [
                x for x in incidents[component]
                if x["recovery"] is None
            ]

            if not unresolved:
                incidents[component].append({
                    "start": ts,
                    "type": "health check failure",
                    "recovery": None,
                })

        elif re.search(
            rf"{component}.*recovery PASSED",
            line,
        ):
            for incident in reversed(incidents[component]):
                if incident["recovery"] is None:
                    incident["recovery"] = ts
                    break


print("COMPONENTS")

for component in COMPONENTS:

    data = incidents[component]

    recovered = sum(
        1 for x in data
        if x["recovery"] is not None
    )

    unresolved = len(data) - recovered

    print(f"  {component}")
    print(f"    Confirmed incidents: {len(data)}")
    print(f"    Recovered:           {recovered}")
    print(f"    Unresolved:          {unresolved}")
    print(
        f"    Page reloads:        "
        f"{page_reloads[component]['health_recovery'] + page_reloads[component]['network_restoration']}"
    )
    print(
        f"      Health recovery:  "
        f"{page_reloads[component]['health_recovery']}"
    )
    print(
        f"      Network restore:  "
        f"{page_reloads[component]['network_restoration']}"
    )

    for i, incident in enumerate(data, 1):

        if incident["recovery"]:

            duration = (
                incident["recovery"] -
                incident["start"]
            )

            print(
                f"      #{i}: {format_time(incident['start'])} "
                f"→ {format_time(incident['recovery'])} "
                f"({duration})"
            )

        else:

            print(
                f"      #{i}: {format_time(incident['start'])} "
                f"→ STILL UNRESOLVED"
            )

print()


# ----------------------------------------------------------------------
# STARTUP CORRELATION
# ----------------------------------------------------------------------

startup_events = []

for component in COMPONENTS:

    for incident in incidents[component]:

        if incident["start"] - start > timedelta(seconds=30):

            matching_start = None

            for event in dashboard_correlations:

                delta = (
                    incident["start"] -
                    event["dashboard_start"]
                )

                if timedelta(seconds=0) <= delta <= timedelta(seconds=30):
                    matching_start = event
                    break

            if matching_start:

                startup_events.append({
                    "component": component,
                    "incident": incident,
                    "dashboard": matching_start,
                })


if startup_events:

    print("STARTUP CORRELATION")

    for event in startup_events:

        incident = event["incident"]
        dashboard = event["dashboard"]

        print(
            f"  {event['component']}: startup incident at "
            f"{format_time(incident['start'])}"
        )

        print(
            f"    Dashboard start: "
            f"{format_time(dashboard['dashboard_start'])}"
        )

        if dashboard["boot"]:

            print(
                f"    Correlation: BOOT #{dashboard['boot']['idx']} "
                f"→ DASHBOARD START"
            )

        else:

            print(
                "    Correlation: DASHBOARD START — NO BOOT MATCH"
            )

    print()


# ----------------------------------------------------------------------
# NETWORK STATE MACHINE
# ----------------------------------------------------------------------

network_events = []

for ts, line in entries:

    result = classify_network(line)

    if result:

        state, gateway, external = result

        network_events.append(
            (ts, state, gateway, external)
        )


network_incidents = []
current = None

for ts, state, gateway, external in network_events:

    if state == "HEALTHY":

        if current:

            current["end"] = ts
            network_incidents.append(current)
            current = None

        continue

    if current is None:

        current = {
            "start": ts,
            "end": None,
            "states": [],
            "max_gateway": gateway,
            "max_external": external,
        }

    current["states"].append(state)
    current["max_gateway"] = max(
        current["max_gateway"],
        gateway,
    )
    current["max_external"] = max(
        current["max_external"],
        external,
    )


if current:
    network_incidents.append(current)


network_degraded = 0
network_failed = 0

print("NETWORK")

if not network_incidents:

    print("  No network degradation or failures detected.")

else:

    for i, incident in enumerate(network_incidents, 1):

        failed = "FAILED" in incident["states"]

        if failed:
            network_failed += 1
        else:
            network_degraded += 1

        state = "FAILURE" if failed else "DEGRADATION"

        if incident["end"]:

            duration = (
                incident["end"] -
                incident["start"]
            )

            ending = (
                f"{format_time(incident['end'])} "
                f"({duration})"
            )

        else:

            ending = "still active at end of log"

        print(
            f"  #{i}: {state} "
            f"{format_time(incident['start'])} → {ending}"
        )

        print(
            f"      Max gateway loss:  "
            f"{incident['max_gateway']:.1f}%"
        )

        print(
            f"      Max external loss: "
            f"{incident['max_external']:.1f}%"
        )

print()

print(
    f"  Degradation incidents:        {network_degraded}"
)

print(
    f"  Failure incidents:            {network_failed}"
)

print()


# ----------------------------------------------------------------------
# ROUTINE / DIAGNOSTIC ACTIVITY
# ----------------------------------------------------------------------

routine_health = 0
routine_network = 0
polling_recovery = 0

for ts, line in entries:

    if "health check PASSED" in line:
        routine_health += 1

    if "NETWORK CHECK:" in line:
        routine_network += 1

    if "rapid polling recovered" in line:
        polling_recovery += 1


print("ROUTINE / DIAGNOSTIC ACTIVITY")
print(
    f"  Successful health checks: {routine_health}"
)
print(
    f"  Network checks:           {routine_network}"
)
print(
    f"  Polling/reinitialization: {polling_recovery}"
)

print()


# ----------------------------------------------------------------------
# DAILY REPORT SUMMARY
# ----------------------------------------------------------------------

unresolved_components = [
    c for c in COMPONENTS
    if any(
        x["recovery"] is None
        for x in incidents[c]
    )
]

dashboard_nonboot_starts = sum(
    1
    for event in dashboard_correlations
    if event["type"] == "DASHBOARD"
)


print("=" * 72)
print("DAILY REPORT SUMMARY")
print("=" * 72)


# PI STABILITY

if len(boots) == 0:
    pi_status = "STABLE — NO REBOOTS DETECTED"
elif len(boots) == 1:
    pi_status = "1 REBOOT DETECTED"
else:
    pi_status = f"{len(boots)} REBOOTS DETECTED"

print(f"PI STABILITY:       {pi_status}")
print(f"  Pi boots:         {len(boots)}")
print()


# DASHBOARD STABILITY

if dashboard_nonboot_starts == 0:
    dashboard_status = "STABLE"
else:
    dashboard_status = (
        f"{dashboard_nonboot_starts} NON-BOOT RESTART(S)"
    )

print(f"DASHBOARD:          {dashboard_status}")
print(f"  Service starts:   {service_starts}")
print(f"  Service stops:    {service_stops}")
print(f"  Process instances:{len(pids)}")
print()


# COMPONENT HEALTH

print("COMPONENT HEALTH:")

for component in COMPONENTS:

    count = len(incidents[component])

    unresolved = sum(
        1
        for x in incidents[component]
        if x["recovery"] is None
    )

    if unresolved:

        state = (
            f"ATTENTION — {unresolved} UNRESOLVED"
        )

    elif count:

        state = (
            f"{count} INCIDENT(S), ALL RECOVERED"
        )

    else:

        state = "NO INCIDENTS"

    print(
        f"  {component:<18} {state}"
    )

print()


# NETWORK HEALTH

if network_failed:

    network_status = (
        f"ATTENTION — {network_failed} FAILURE(S)"
    )

elif network_degraded:

    network_status = (
        f"DEGRADED — {network_degraded} INCIDENT(S)"
    )

else:

    network_status = "HEALTHY"

print(f"NETWORK:            {network_status}")
print(f"  Degradations:     {network_degraded}")
print(f"  Failures:         {network_failed}")
print()


# OVERALL STATUS

if (
    len(boots) > 0
    or dashboard_nonboot_starts > 0
    or unresolved_components
):

    overall_status = "ATTENTION REQUIRED"

elif network_failed > 0 or network_degraded > 0:

    overall_status = (
        "NETWORK INCIDENTS — OTHERWISE STABLE"
    )

else:

    overall_status = "HEALTHY"


print(f"OVERALL STATUS:     {overall_status}")
print()

# ----------------------------------------------------------------------
# EMAIL REPORT
# ----------------------------------------------------------------------

if "--email" in sys.argv:

    now = datetime.now(LOCAL_TZ)
    period_start = now - timedelta(hours=24)

    print("STATION DASHBOARD")
    print("Daily Health Report")
    print()
    print(
        f"{period_start.strftime('%b %-d, %-I:%M %p')} "
        f"→ {now.strftime('%b %-d, %-I:%M %p')}"
    )
    print()
    print("OVERALL STATUS")
    print(overall_status)
    print()

    print("SYSTEM")
    print(f"• Pi reboots: {len(boots)}")
    print(f"• Dashboard restarts: {dashboard_nonboot_starts}")
    print()

    print("COMPONENT HEALTH")

    for component in COMPONENTS:

        data = incidents[component]
        count = len(data)

        recovered = sum(
            1
            for x in data
            if x["recovery"] is not None
        )

        unresolved = count - recovered

        reloads = (
            page_reloads[component]["health_recovery"]
            + page_reloads[component]["network_restoration"]
        )

        print()
        print(component)

        if unresolved:
            print(f"⚠️ {unresolved} unresolved")
        elif count:
            print(f"✓ {count} incidents — all recovered")
        else:
            print("✓ No incidents")

        if reloads:
            print(f"↻ {reloads} page reloads")

        if count and recovered == count:
            durations = [
                int(
                    (
                        x["recovery"] - x["start"]
                    ).total_seconds()
                )
                for x in data
                if x["recovery"] is not None
            ]

            if durations:
                print(
                    f"Recovery: {min(durations)}–{max(durations)} sec"
                )

    print()
    print("NETWORK")

    if network_failed or network_degraded:
        print(f"⚠️ {network_failed} failures")
        print(f"⚠️ {network_degraded} degradations")
    else:
        print("✓ No network incidents")

    print()
    print("RELIABILITY")
    print(f"Health checks: {routine_health:,}")
    print(f"Network checks: {routine_network:,}")
    print(f"Polling/recovery: {polling_recovery}")

    notable = []

    for component in COMPONENTS:

        data = incidents[component]

        for x in data:
            if x["recovery"] is None:
                notable.append(
                    f"{component} became unhealthy at "
                    f"{format_time(x['start'])} and remains unresolved."
                )

    if dashboard_nonboot_starts:
        notable.append(
            f"{dashboard_nonboot_starts} non-boot dashboard restart(s) occurred."
        )

    if network_failed:
        notable.append(
            f"{network_failed} network failure(s) were detected."
        )

    print()

    if notable:
        print("NOTABLE EVENTS")

        for item in notable:
            print(f"• {item}")

    print()
    print(
        f"Generated: {now.strftime('%b %-d, %-I:%M %p')}"
    )

    sys.exit(0)


print("=" * 72)
print("ANALYSIS COMPLETE")
print("=" * 72)
