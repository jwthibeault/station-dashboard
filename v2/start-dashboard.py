import json
import subprocess
import sys
import threading
import time
import urllib.request
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


def initialize_dashboard(
    name,
    config,
    credentials,
    results,
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
            print(f"{name} initialization PASSED.")

    except Exception as e:
        results[name] = False

        print(f"{name} initialization FAILED: {e}")
        print(
            f"{name} will remain isolated from "
            "the other dashboards."
        )


def main():
    print("===== V2.1 INDEPENDENT INITIALIZATION TEST =====")

    processes = {}
    initialization_results = {}

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
    print("This test does not yet perform continuous")
    print("health monitoring or automatic recovery.")
    print()
    print("Press Enter to stop the V2.1 test...")

    input()

    #
    # Stop all Chromium windows.
    #
    print()
    print("Stopping V2 Chromium windows...")

    for process in processes.values():
        process.terminate()

    print("Stopping V2 wrapper server...")
    wrapper_process.terminate()


if __name__ == "__main__":
    main()
