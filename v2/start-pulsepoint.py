import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright

from station_dashboard.pulsepoint import PulsePoint


def main():
    credentials = {}

    credentials_file = BASE_DIR / "credentials.json"

    if credentials_file.exists():
        with open(credentials_file) as f:
            all_credentials = json.load(f)

        credentials = all_credentials.get(
            "pulsepoint",
            {}
        )

    with sync_playwright() as p:
        print(
            "Connecting to PulsePoint Chromium "
            "on CDP port 9233..."
        )

        browser = p.chromium.connect_over_cdp(
            "http://127.0.0.1:9233"
        )

        context = browser.contexts[0]

        pages = [
            page for page in context.pages
            if page.url.startswith("http")
        ]

        if not pages:
            raise RuntimeError(
                "No HTTP page found in PulsePoint Chromium."
            )

        page = pages[0]

        print(f"PulsePoint page: {page.url}")

        pulsepoint = PulsePoint(
            page,
            credentials
        )

        print("Initializing PulsePoint...")
        pulsepoint.open()

        print("Checking PulsePoint...")
        healthy = pulsepoint.check()

        print(
            f"PulsePoint health check result: "
            f"{healthy}"
        )

        if not healthy:
            raise RuntimeError(
                "PulsePoint health check failed."
            )

        print("PulsePoint health check passed.")

        input(
            "Press Enter to disconnect from PulsePoint..."
        )


if __name__ == "__main__":
    main()
