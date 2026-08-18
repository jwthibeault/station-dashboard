import json
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright

from station_dashboard.bloomwx import BloomWX
from station_dashboard.iamresponding import IamResponding
from station_dashboard.vdot import VDOT


BLOOMWX_URL = "http://127.0.0.1:8082/bloomwx.html"
BLOOMWX_PROFILE = "/tmp/v2-bloomwx-profile"
BLOOMWX_PORT = 9230

VDOT_URL = "http://127.0.0.1:8082/vdot.html"
VDOT_PROFILE = "/tmp/v2-vdot-profile"
VDOT_PORT = 9231

IAMRESPONDING_URL = "http://127.0.0.1:8082/iamresponding.html"
IAMRESPONDING_PROFILE = "/tmp/v2-iamresponding-profile"
IAMRESPONDING_PORT = 9232

PULSEPOINT_URL = "http://127.0.0.1:8082/pulsepoint.html"
PULSEPOINT_PROFILE = "/tmp/v2-pulsepoint-profile"
PULSEPOINT_PORT = 9233


def wait_for_cdp(port, timeout=30):
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{port}"
                )
                browser.close()

            return True

        except Exception:
            time.sleep(0.5)

    return False


def start_window(url, profile, port, log_file):
    command = [
        str(BASE_DIR / "scripts/start-v2-window.sh"),
        url,
        profile,
        str(port),
    ]

    return subprocess.Popen(
        command,
        stdout=open(log_file, "a"),
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


def main():
    print("===== V2 FOUR-QUADRANT DASHBOARD =====")

    print("Starting BloomWX Chromium...")
    bloom_process = start_window(
        BLOOMWX_URL,
        BLOOMWX_PROFILE,
        BLOOMWX_PORT,
        "/tmp/v2-bloomwx-launch.log",
    )

    print("Waiting for BloomWX CDP...")
    if not wait_for_cdp(BLOOMWX_PORT):
        raise RuntimeError("BloomWX Chromium did not start.")

    print("BloomWX Chromium is ready.")

    print("Starting VDOT Chromium...")
    vdot_process = start_window(
        VDOT_URL,
        VDOT_PROFILE,
        VDOT_PORT,
        "/tmp/v2-vdot-launch.log",
    )

    print("Waiting for VDOT CDP...")
    if not wait_for_cdp(VDOT_PORT):
        raise RuntimeError("VDOT Chromium did not start.")

    print("VDOT Chromium is ready.")

    print("Starting IamResponding Chromium...")
    iam_process = start_window(
        IAMRESPONDING_URL,
        IAMRESPONDING_PROFILE,
        IAMRESPONDING_PORT,
        "/tmp/v2-iamresponding-launch.log",
    )

    print("Waiting for IamResponding CDP...")
    if not wait_for_cdp(IAMRESPONDING_PORT):
        raise RuntimeError("IamResponding Chromium did not start.")

    print("IamResponding Chromium is ready.")

    print("Starting PulsePoint Chromium...")
    pulse_process = start_window(
        PULSEPOINT_URL,
        PULSEPOINT_PROFILE,
        PULSEPOINT_PORT,
        "/tmp/v2-pulsepoint-launch.log",
    )

    print("Waiting for PulsePoint CDP...")
    if not wait_for_cdp(PULSEPOINT_PORT):
        raise RuntimeError("PulsePoint Chromium did not start.")

    print("PulsePoint Chromium is ready.")

    print()
    print("All four V2 Chromium windows are running.")
    print()

    with open(BASE_DIR / "credentials.json") as f:
        credentials = json.load(f)

    with sync_playwright() as p:

        #
        # VDOT
        #
        print("===== VDOT =====")

        vdot_browser = p.chromium.connect_over_cdp(
            f"http://127.0.0.1:{VDOT_PORT}"
        )

        vdot_page = get_page(
            vdot_browser,
            "VDOT"
        )

        vdot = VDOT(
            vdot_page,
            credentials["vdot"]
        )

        print("Opening VDOT camera wall...")
        vdot.open()
        print("VDOT camera wall initialized successfully.")

        #
        # IamResponding
        #
        print()
        print("===== IAMRESPONDING =====")

        iam_browser = p.chromium.connect_over_cdp(
            f"http://127.0.0.1:{IAMRESPONDING_PORT}"
        )

        iam_page = get_page(
            iam_browser,
            "IamResponding"
        )

        iam = IamResponding(
            iam_page,
            credentials["iamresponding"]
        )

        print("Opening IamResponding...")
        iam.open()

        print("Checking IamResponding...")
        iam_healthy = iam.check()

        print(
            f"IamResponding health check result: "
            f"{iam_healthy}"
        )

        if not iam_healthy:
            raise RuntimeError(
                "IamResponding health check failed."
            )

        print("IamResponding health check passed.")

        #
        # BloomWX
        #
        print()
        print("===== BLOOMWX =====")

        bloom_browser = p.chromium.connect_over_cdp(
            f"http://127.0.0.1:{BLOOMWX_PORT}"
        )

        bloom_page = get_page(
            bloom_browser,
            "BloomWX"
        )

        bloomwx = BloomWX(bloom_page)

        print("Checking BloomWX...")
        bloom_healthy = bloomwx.check()

        print(
            f"BloomWX health check result: "
            f"{bloom_healthy}"
        )

        if not bloom_healthy:
            raise RuntimeError(
                "BloomWX health check failed."
            )

        print("BloomWX health check passed.")

        #
        # PulsePoint
        #
        print()
        print("===== PULSEPOINT =====")
        print("PulsePoint placeholder is running.")

        print()
        print("========================================")
        print("V2 FOUR-QUADRANT DASHBOARD READY")
        print("========================================")
        print("BloomWX:        TOP LEFT")
        print("VDOT:           TOP RIGHT")
        print("IamResponding:  BOTTOM LEFT")
        print("PulsePoint:     BOTTOM RIGHT")
        print()
        print("No dashboard rotation.")
        print("No emergency-mode rotation handling.")
        print()

        input("Press Enter to stop the V2 test...")

    print("Stopping V2 Chromium windows...")

    bloom_process.terminate()
    vdot_process.terminate()
    iam_process.terminate()
    pulse_process.terminate()


if __name__ == "__main__":
    main()
