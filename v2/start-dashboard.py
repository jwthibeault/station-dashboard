import json
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright

from station_dashboard.bloomwx import BloomWX
from station_dashboard.iamresponding import IamResponding
from station_dashboard.vdot import VDOT


DASHBOARDS = {
    "BloomWX": {
        "url": "http://127.0.0.1:8082/bloomwx.html",
        "profile": "/tmp/v2-bloomwx-profile",
        "port": 9230,
        "log": "/tmp/v2-bloomwx-launch.log",
    },
    "VDOT": {
        "url": "http://127.0.0.1:8082/vdot.html",
        "profile": "/tmp/v2-vdot-profile",
        "port": 9231,
        "log": "/tmp/v2-vdot-launch.log",
    },
    "IamResponding": {
        "url": "http://127.0.0.1:8082/iamresponding.html",
        "profile": "/tmp/v2-iamresponding-profile",
        "port": 9232,
        "log": "/tmp/v2-iamresponding-launch.log",
    },
    "PulsePoint": {
        "url": "http://127.0.0.1:8082/pulsepoint.html",
        "profile": "/tmp/v2-pulsepoint-profile",
        "port": 9233,
        "log": "/tmp/v2-pulsepoint-launch.log",
    },
}


WRAPPER_DIR = BASE_DIR / "v2" / "windows"
WRAPPER_PORT = 8082
WRAPPER_LOG = "/tmp/v2-wrapper-server.log"


def wait_for_wrapper_server(timeout=10):
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{WRAPPER_PORT}/bloomwx.html"

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                url,
                timeout=1,
            ) as response:
                if response.status == 200:
                    return True

        except Exception:
            pass

        time.sleep(0.5)

    return False


def start_wrapper_server():
    command = [
        sys.executable,
        "-m",
        "http.server",
        str(WRAPPER_PORT),
        "--directory",
        str(WRAPPER_DIR),
    ]

    return subprocess.Popen(
        command,
        stdout=open(WRAPPER_LOG, "a"),
        stderr=subprocess.STDOUT,
    )


def wait_for_cdp(port, timeout=30):
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/json/version"

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                url,
                timeout=1,
            ) as response:
                if response.status == 200:
                    return True

        except Exception:
            pass

        time.sleep(0.5)

    return False


def start_window(config):
    command = [
        str(BASE_DIR / "scripts/start-v2-window.sh"),
        config["url"],
        config["profile"],
        str(config["port"]),
    ]

    return subprocess.Popen(
        command,
        stdout=open(config["log"], "a"),
        stderr=subprocess.STDOUT,
    )


def get_page(browser, name):
    context = browser.contexts[0]

    pages = [
        page for page in context.pages
        if page.url.startswith("http")
    ]

    if not pages:
        raise RuntimeError(
            f"No HTTP page found in {name} Chromium."
        )

    page = pages[0]

    print(f"{name} page: {page.url}")

    return page


def wait_for_real_page(page, name, timeout=30):
    print(f"Waiting for {name} wrapper redirect...")

    deadline = time.time() + timeout

    while time.time() < deadline:
        if page.is_closed():
            raise RuntimeError(
                f"{name} page closed during wrapper redirect."
            )

        url = page.url

        if not url.startswith(
            "http://127.0.0.1:8082/"
        ):
            print(f"{name} real page reached: {url}")
            return

        time.sleep(0.5)

    raise RuntimeError(
        f"{name} wrapper did not redirect within "
        f"{timeout} seconds."
    )


def initialize_bloomwx(browser):
    page = get_page(browser, "BloomWX")

    print(
        "Skipping wrapper readiness wait for BloomWX; "
        "using V1.5.1 load and health flow."
    )

    bloomwx = BloomWX(page)

    print("Opening BloomWX...")
    if not bloomwx.open():
        raise RuntimeError(
            "BloomWX failed to load."
        )

    print("Checking BloomWX...")
    healthy = bloomwx.check()

    print(f"BloomWX health check result: {healthy}")

    if not healthy:
        raise RuntimeError("BloomWX health check failed.")

    print("BloomWX health check passed.")


def initialize_vdot(browser, credentials):
    page = get_page(browser, "VDOT")

    print(
        "Skipping wrapper readiness wait for VDOT; "
        "using known-good navigation and login flow."
    )

    vdot = VDOT(
        page,
        credentials["vdot"]
    )

    print("Opening VDOT camera wall...")
    vdot.open()

    print("VDOT camera wall initialized successfully.")


def initialize_iamresponding(browser, credentials):
    page = get_page(browser, "IamResponding")

    print(
        "Skipping wrapper readiness wait for IamResponding; "
        "using known-good login flow."
    )

    iam = IamResponding(
        page,
        credentials["iamresponding"]
    )

    print("Opening IamResponding...")
    iam.open()

    print("Checking IamResponding...")
    healthy = iam.check()

    print(
        f"IamResponding health check result: "
        f"{healthy}"
    )

    if not healthy:
        raise RuntimeError(
            "IamResponding health check failed."
        )

    print("IamResponding health check passed.")


def initialize_pulsepoint(browser):
    page = get_page(browser, "PulsePoint")

    print(f"PulsePoint page: {page.url}")
    print("PulsePoint placeholder is running.")


def record_successful_check(health_state, name):
    health_state[name] = {
        "healthy": True,
        "last_successful_check": datetime.now().astimezone(),
    }


def initialize_dashboard(
    name,
    config,
    credentials,
    results,
    health_state,
):
    print()
    print(f"--- {name} ---")

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(
                f"http://127.0.0.1:{config['port']}"
            )

            if name == "BloomWX":
                initialize_bloomwx(browser)

            elif name == "VDOT":
                initialize_vdot(
                    browser,
                    credentials
                )

            elif name == "IamResponding":
                initialize_iamresponding(
                    browser,
                    credentials
                )

            elif name == "PulsePoint":
                initialize_pulsepoint(browser)

            results[name] = True
            record_successful_check(
                health_state,
                name,
            )

            print(f"{name} initialization PASSED.")
            print(
                f"{name} last successful health check: "
                f"{health_state[name]['last_successful_check'].strftime('%Y-%m-%d %I:%M:%S %p')}"
            )

    except Exception as e:
        results[name] = False

        print(f"{name} initialization FAILED: {e}")
        print(
            f"{name} will remain isolated from "
            "the other dashboards."
        )


MONITOR_INTERVAL = 30
CDP_RECONNECT_DELAY = 5

# Network health monitoring.
NETWORK_CHECK_INTERVAL = 5
NETWORK_CHECK_COUNT = 4
NETWORK_CHECK_TIMEOUT = 2
NETWORK_FAILURE_THRESHOLD = 2
NETWORK_RECOVERY_THRESHOLD = 2
NETWORK_REBOOT_SECONDS = 3600
NETWORK_EXTERNAL_TARGET = "1.1.1.1"

# Packet-loss thresholds used to determine network availability.
# The local gateway must have zero packet loss. A small amount
# of Internet packet loss is tolerated because ICMP loss does
# not necessarily mean the Internet connection is unavailable.
NETWORK_GATEWAY_MAX_PACKET_LOSS = 0.0
NETWORK_EXTERNAL_MAX_PACKET_LOSS = 25.0


def get_default_gateway():
    try:
        result = subprocess.run(
            [
                "ip",
                "route",
                "show",
                "default",
            ],
            capture_output=True,
            text=True,
            timeout=NETWORK_CHECK_TIMEOUT,
            check=False,
        )

        for line in result.stdout.splitlines():
            parts = line.split()

            if "default" in parts and "via" in parts:
                return parts[parts.index("via") + 1]

    except Exception as e:
        print(f"Could not determine default gateway: {e}")

    return None


def ping_host(host):
    try:
        result = subprocess.run(
            [
                "ping",
                "-c",
                str(NETWORK_CHECK_COUNT),
                "-W",
                str(NETWORK_CHECK_TIMEOUT),
                host,
            ],
            capture_output=True,
            text=True,
            timeout=(
                NETWORK_CHECK_COUNT
                * NETWORK_CHECK_TIMEOUT
                + 2
            ),
            check=False,
        )

        output = result.stdout + result.stderr

        packet_loss = None

        for line in output.splitlines():
            if "packet loss" in line:
                try:
                    packet_loss = float(
                        line.split("%")[0].split()[-1]
                    )
                except (ValueError, IndexError):
                    pass

                break

        return {
            "reachable": result.returncode == 0,
            "packet_loss": packet_loss,
            "output": output,
        }

    except Exception as e:
        return {
            "reachable": False,
            "packet_loss": None,
            "output": str(e),
        }


def check_network():
    gateway = get_default_gateway()

    if gateway is None:
        return {
            "available": False,
            "gateway": None,
            "gateway_result": None,
            "external_result": None,
        }

    gateway_result = ping_host(gateway)
    external_result = ping_host(
        NETWORK_EXTERNAL_TARGET
    )

    gateway_loss = gateway_result["packet_loss"]
    external_loss = external_result["packet_loss"]

    gateway_available = (
        gateway_result["reachable"]
        and gateway_loss is not None
        and gateway_loss <= NETWORK_GATEWAY_MAX_PACKET_LOSS
    )

    external_available = (
        external_result["reachable"]
        and external_loss is not None
        and external_loss <= NETWORK_EXTERNAL_MAX_PACKET_LOSS
    )

    available = (
        gateway_available
        and external_available
    )

    print(
        "NETWORK CHECK: "
        f"gateway={gateway} "
        f"gateway_loss={gateway_result['packet_loss']}% "
        f"external={NETWORK_EXTERNAL_TARGET} "
        f"external_loss={external_result['packet_loss']}% "
        f"available={available}"
    )

    return {
        "available": available,
        "gateway": gateway,
        "gateway_result": gateway_result,
        "external_result": external_result,
    }


def format_health_time(value):
    if value is None:
        return "No successful health check recorded."

    return value.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def show_dashboard_down(
    page,
    name,
    health_state,
    reason="WEBSITE OUTAGE",
    network_result=None,
):
    last_successful = health_state.get(name, {}).get(
        "last_successful_check"
    )

    timestamp = format_health_time(last_successful)

    down_url = (
        "http://127.0.0.1:8082/dashboard-down.html"
        f"?site={name}"
        f"&last_successful={timestamp}"
        f"&reason={reason}"
    )

    if network_result is not None:
        gateway = network_result.get("gateway")
        gateway_result = network_result.get(
            "gateway_result"
        ) or {}
        external_result = network_result.get(
            "external_result"
        ) or {}

        gateway_loss = gateway_result.get(
            "packet_loss"
        )
        external_target = NETWORK_EXTERNAL_TARGET
        external_loss = external_result.get(
            "packet_loss"
        )

        down_url += (
            f"&gateway={gateway or 'NONE'}"
            f"&gateway_loss={gateway_loss if gateway_loss is not None else 'UNKNOWN'}"
            f"&external={external_target}"
            f"&external_loss={external_loss if external_loss is not None else 'UNKNOWN'}"
        )

    #
    # Do not repeatedly reload the same DOWN page. However, if
    # the reason has changed (for example WEBSITE OUTAGE ->
    # NETWORK OUTAGE), replace the page so the displayed reason
    # remains accurate.
    #
    if page.url.startswith(
        "http://127.0.0.1:8082/dashboard-down.html"
    ):
        current_reason = None

        try:
            current_reason = (
                page.url.split("reason=", 1)[1]
                .split("&", 1)[0]
            )
        except (IndexError, ValueError):
            pass

        if current_reason == reason:
            return

    print(
        f"{name} is DOWN. "
        f"Last successful health check: {timestamp}"
    )

    page.goto(
        down_url,
        wait_until="domcontentloaded",
        timeout=10000,
    )


def create_dashboard(name, page, credentials):
    if name == "BloomWX":
        return BloomWX(page)

    if name == "VDOT":
        return VDOT(
            page,
            credentials["vdot"],
        )

    if name == "IamResponding":
        return IamResponding(
            page,
            credentials["iamresponding"],
        )

    if name == "PulsePoint":
        return None

    raise RuntimeError(
        f"Unknown dashboard: {name}"
    )


def recover_dashboard(
    name,
    dashboard,
    page,
    health_state,
):
    print(
        f"{name} health check FAILED. "
        "Attempting recovery..."
    )

    try:
        if not dashboard.open():
            print(
                f"{name} recovery open() returned False."
            )
            return False

        print(
            f"{name} recovery navigation completed. "
            f"Waiting {MONITOR_INTERVAL} seconds before "
            "resuming health checks."
        )

        time.sleep(MONITOR_INTERVAL)

        healthy = dashboard.check()

        if healthy:
            record_successful_check(
                health_state,
                name,
            )

            print(
                f"{name} recovery PASSED. "
                f"Last successful health check: "
                f"{format_health_time(health_state[name]['last_successful_check'])}"
            )

            return True

        print(
            f"{name} recovery check FAILED after "
            f"{MONITOR_INTERVAL}-second grace period."
        )

        return False

    except Exception as recovery_error:
        print(
            f"{name} recovery failed: "
            f"{recovery_error}"
        )
        return False


def monitor_dashboard(
    name,
    config,
    credentials,
    health_state,
    initialization_results,
    network_down,
    network_restore_generation,
    network_status,
):
    print(f"{name} health monitor started.")

    while True:
        try:
            with sync_playwright() as p:
                print(
                    f"{name} monitor connecting to "
                    f"CDP {config['port']}..."
                )

                browser = p.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{config['port']}"
                )

                page = get_page(
                    browser,
                    name,
                )

                dashboard = create_dashboard(
                    name,
                    page,
                    credentials,
                )

                if dashboard is None:
                    print(
                        f"{name} monitoring is currently "
                        "placeholder-only."
                    )

                    while True:
                        time.sleep(MONITOR_INTERVAL)

                print(
                    f"{name} continuous health monitoring "
                    "active."
                )

                if not initialization_results.get(name, False):
                    print(
                        f"{name} initialization previously failed. "
                        f"Waiting {MONITOR_INTERVAL} seconds before "
                        "the first health check."
                    )

                    time.sleep(MONITOR_INTERVAL)

                    print(
                        f"{name} startup grace period complete. "
                        "Beginning health checks."
                    )

                down = False
                consecutive_failures = 0
                was_network_down = False
                last_restore_generation = network_restore_generation["value"]

                while True:
                    try:
                        #
                        # NETWORK DOWN:
                        #
                        # Do not attempt website recovery while the
                        # network itself is unavailable. Keep the
                        # browser on our local DOWN page.
                        #
                        if network_down.is_set():
                            if not was_network_down:
                                network_result = network_status["value"]

                                print(
                                    f"{name}: network is DOWN. "
                                    "Showing WEBSITE UNAVAILABLE."
                                )

                                try:
                                    show_dashboard_down(
                                        page,
                                        name,
                                        health_state,
                                        reason="NETWORK OUTAGE",
                                        network_result=network_result,
                                    )
                                except Exception as down_error:
                                    print(
                                        f"{name} could not display "
                                        f"the website-down page: "
                                        f"{down_error}"
                                    )

                                was_network_down = True
                                down = True
                                consecutive_failures = 0

                            time.sleep(2)
                            continue

                        #
                        # NETWORK RESTORED:
                        #
                        # The network monitor increments a shared
                        # generation counter exactly once for each
                        # network restoration. Every dashboard sees
                        # that same restoration event and reloads.
                        #
                        current_restore_generation = (
                            network_restore_generation["value"]
                        )

                        if (
                            was_network_down
                            or current_restore_generation
                            != last_restore_generation
                        ):
                            print(
                                f"{name}: network restored. "
                                "Reloading dashboard..."
                            )

                            try:
                                if dashboard is not None:
                                    dashboard.open()

                                print(
                                    f"{name}: reload completed. "
                                    f"Waiting {MONITOR_INTERVAL} seconds "
                                    "before health checks resume."
                                )

                                time.sleep(MONITOR_INTERVAL)

                                if dashboard is None:
                                    healthy = True
                                else:
                                    healthy = dashboard.check()

                                if healthy:
                                    record_successful_check(
                                        health_state,
                                        name,
                                    )

                                    print(
                                        f"{name} recovery PASSED. "
                                        "Returning to normal monitoring."
                                    )

                                    down = False
                                    consecutive_failures = 0
                                    was_network_down = False
                                    last_restore_generation = (
                                        current_restore_generation
                                    )

                                else:
                                    print(
                                        f"{name} recovery check FAILED "
                                        "after network restoration."
                                    )

                                    down = True
                                    was_network_down = False
                                    consecutive_failures = 1
                                    last_restore_generation = (
                                        current_restore_generation
                                    )

                            except Exception as recovery_error:
                                print(
                                    f"{name} recovery after network "
                                    f"restoration failed: {recovery_error}"
                                )

                                show_dashboard_down(
                                    page,
                                    name,
                                    health_state,
                                )

                                down = True
                                was_network_down = False
                                consecutive_failures = 1
                                last_restore_generation = (
                                    current_restore_generation
                                )

                            time.sleep(1)
                            continue

                        #
                        # NORMAL INDIVIDUAL SITE MONITORING:
                        #
                        healthy = dashboard.check()

                        if healthy:
                            record_successful_check(
                                health_state,
                                name,
                            )

                            consecutive_failures = 0

                            if down:
                                print(
                                    f"{name} recovery PASSED. "
                                    "Returning to normal health monitoring."
                                )

                            down = False

                            print(
                                f"{name} health check PASSED: "
                                f"{format_health_time(health_state[name]['last_successful_check'])}"
                            )

                        else:
                            consecutive_failures += 1

                            print(
                                f"{name} health check FAILED "
                                f"({consecutive_failures} consecutive)."
                            )

                            if consecutive_failures < 2:
                                print(
                                    f"{name} will wait for one more "
                                    "consecutive failed health check "
                                    "before attempting recovery."
                                )

                            elif not down:
                                recovered = recover_dashboard(
                                    name,
                                    dashboard,
                                    page,
                                    health_state,
                                )

                                if recovered:
                                    consecutive_failures = 0
                                    down = False

                                else:
                                    down = True

                                    show_dashboard_down(
                                        page,
                                        name,
                                        health_state,
                                    )

                                    print(
                                        f"{name} remains DOWN. "
                                        "Continuing health monitoring."
                                    )

                            else:
                                print(
                                    f"{name} remains DOWN. "
                                    "Attempting individual recovery..."
                                )

                                recovered = recover_dashboard(
                                    name,
                                    dashboard,
                                    page,
                                    health_state,
                                )

                                if recovered:
                                    consecutive_failures = 0
                                    down = False

                                else:
                                    show_dashboard_down(
                                        page,
                                        name,
                                        health_state,
                                    )

                                    print(
                                        f"{name} remains DOWN. "
                                        "Continuing health monitoring."
                                    )

                        time.sleep(MONITOR_INTERVAL)

                    except Exception as check_error:
                        print(
                            f"{name} health-monitoring "
                            f"error: {check_error}"
                        )

                        try:
                            show_dashboard_down(
                                page,
                                name,
                                health_state,
                            )
                        except Exception as down_error:
                            print(
                                f"{name} could not display "
                                f"the website-down page: "
                                f"{down_error}"
                            )

                        time.sleep(MONITOR_INTERVAL)

        except Exception as connection_error:
            print(
                f"{name} monitor connection lost: "
                f"{connection_error}"
            )

            print(
                f"{name} will retry its CDP connection "
                f"in {CDP_RECONNECT_DELAY} seconds."
            )

            time.sleep(CDP_RECONNECT_DELAY)


def start_health_monitors(
    credentials,
    health_state,
    initialization_results,
):
    print()
    print(
        "===== STARTING CONTINUOUS HEALTH MONITORING ====="
    )

    network_down = threading.Event()

    #
    # Latest network diagnostic result. This is shared with the
    # dashboard monitors so their DOWN pages can identify the
    # network condition that caused the outage.
    #
    network_status = {
        "value": None,
    }

    #
    # Incremented once each time the network transitions from
    # unavailable to available. All dashboard monitors observe
    # the same generation and therefore all reload after the
    # same restoration event.
    #
    network_restore_generation = {
        "value": 0,
    }

    def monitor_network():
        last_state = None
        consecutive_failures = 0
        consecutive_successes = 0
        outage_started = None

        while True:
            result = check_network()
            network_status["value"] = result
            available = result["available"]

            if available:
                consecutive_failures = 0
                consecutive_successes += 1

                if (
                    last_state is False
                    and consecutive_successes
                    >= NETWORK_RECOVERY_THRESHOLD
                ):
                    network_restore_generation["value"] += 1

                    print(
                        "NETWORK RESTORED. "
                        "All dashboard monitors will reload their pages."
                    )

                    print(
                        "Network restoration generation: "
                        f"{network_restore_generation['value']}"
                    )

                    network_down.clear()
                    last_state = True
                    outage_started = None

                elif last_state is None:
                    print(
                        "NETWORK AVAILABLE. "
                        "Initial network state established."
                    )

                    network_down.clear()
                    last_state = True

                elif last_state is True:
                    network_down.clear()

            else:
                consecutive_successes = 0
                consecutive_failures += 1

                if (
                    last_state is not False
                    and consecutive_failures
                    >= NETWORK_FAILURE_THRESHOLD
                ):
                    outage_started = time.monotonic()

                    print(
                        "NETWORK OUTAGE CONFIRMED. "
                        "All dashboard monitors will stop "
                        "individual recovery."
                    )

                    network_down.set()
                    last_state = False

                elif last_state is False:
                    network_down.set()

                if (
                    last_state is False
                    and outage_started is not None
                    and (
                        time.monotonic()
                        - outage_started
                    ) >= NETWORK_REBOOT_SECONDS
                ):
                    print(
                        "NETWORK OUTAGE HAS EXCEEDED "
                        "ONE HOUR. REBOOTING PI."
                    )

                    subprocess.Popen(
                        [
                            "sudo",
                            "reboot",
                        ]
                    )

                    return

            time.sleep(NETWORK_CHECK_INTERVAL)

    network_thread = threading.Thread(
        target=monitor_network,
        name="monitor-network",
        daemon=True,
    )

    network_thread.start()

    monitor_threads = []

    for name, config in DASHBOARDS.items():
        thread = threading.Thread(
            target=monitor_dashboard,
            args=(
                name,
                config,
                credentials,
                health_state,
                initialization_results,
                network_down,
                network_restore_generation,
                network_status,
            ),
            name=f"monitor-{name}",
            daemon=True,
        )

        monitor_threads.append(thread)
        thread.start()

    print(
        f"Continuous health monitoring active "
        f"(every {MONITOR_INTERVAL} seconds)."
    )

    return monitor_threads


def main():
    print("===== V2.1 INDEPENDENT INITIALIZATION TEST =====")

    processes = {}
    initialization_results = {}
    health_state = {}

    #
    # Start the local wrapper server first.
    #
    print()
    print("===== STARTING WRAPPER SERVER =====")

    wrapper_process = start_wrapper_server()

    print("Waiting for wrapper server...")

    if not wait_for_wrapper_server():
        wrapper_process.terminate()
        raise RuntimeError(
            "V2 wrapper server did not start."
        )

    print("V2 wrapper server is ready.")

    #
    # Start all four Chromium windows.
    #
    print()
    print("===== STARTING CHROMIUM WINDOWS =====")

    for name, config in DASHBOARDS.items():
        print(f"Starting {name} Chromium...")

        processes[name] = start_window(config)

        # Give Labwc time to apply the window placement rule
        # before creating the next Chromium window.
        if name != list(DASHBOARDS.keys())[-1]:
            time.sleep(2)

    #
    # Wait for every CDP endpoint independently.
    #
    print()
    print("===== WAITING FOR CDP =====")

    for name, config in DASHBOARDS.items():
        print(f"Waiting for {name} CDP...")

        if wait_for_cdp(config["port"]):
            print(f"{name} Chromium is ready.")
        else:
            print(f"{name} Chromium FAILED to start.")

    print()
    print("All Chromium startup attempts completed.")

    with open(BASE_DIR / "credentials.json") as f:
        credentials = json.load(f)

    #
    # Initialize every dashboard concurrently.
    # Each thread owns its own Playwright connection.
    #
    print()
    print("===== INITIALIZING DASHBOARDS CONCURRENTLY =====")

    threads = []

    for name, config in DASHBOARDS.items():
        thread = threading.Thread(
            target=initialize_dashboard,
            args=(
                name,
                config,
                credentials,
                initialization_results,
                health_state,
            ),
            name=f"v2-{name}",
        )

        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    #
    # Summary
    #
    print()
    print("========================================")
    print("V2.1 INITIALIZATION RESULTS")
    print("========================================")

    for name in DASHBOARDS:
        result = initialization_results.get(
            name,
            False
        )

        status = "PASS" if result else "FAILED"

        print(f"{name:16} {status}")

    print()

    failed_dashboards = [
        name
        for name in DASHBOARDS
        if not initialization_results.get(name, False)
    ]

    if failed_dashboards:
        print(
            "Initialization failures detected: "
            + ", ".join(failed_dashboards)
        )

        for name in failed_dashboards:
            print(
                f"{name} will be monitored and "
                "shown as WEBSITE DOWN until recovery."
            )

    start_health_monitors(
        credentials,
        health_state,
        initialization_results,
    )

    print()
    print("===== V2.1 DASHBOARD RUNNING =====")
    print(
        "Continuous health monitoring and "
        "automatic recovery are active."
    )
    print(
        f"Health checks run every {MONITOR_INTERVAL} seconds."
    )
    print()
    print(
        "V2 dashboard is now managed by dashboardctl."
    )
    print(
        "Use './tools/dashboardctl v2-stop' "
        "to stop V2."
    )

    #
    # Keep the main V2 process alive.
    # dashboardctl v2-stop is responsible for stopping
    # the V2 Chromium windows and wrapper server.
    #
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
