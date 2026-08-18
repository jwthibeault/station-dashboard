import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright

from station_dashboard.vdot import VDOT


def main():
    with open(BASE_DIR / "credentials.json") as f:
        credentials = json.load(f)

    with sync_playwright() as p:
        print("Connecting to VDOT Chromium on CDP port 9231...")

        browser = p.chromium.connect_over_cdp(
            "http://127.0.0.1:9231"
        )

        context = browser.contexts[0]

        pages = [
            page for page in context.pages
            if page.url.startswith("http")
        ]

        if not pages:
            raise RuntimeError("No HTTP page found in VDOT Chromium.")

        page = pages[0]

        print(f"VDOT page: {page.url}")

        vdot = VDOT(
            page,
            credentials["vdot"]
        )

        print("Opening VDOT camera wall...")
        vdot.open()

        print("VDOT camera wall initialized successfully.")

        input("Press Enter to disconnect from VDOT...")

        browser.close()


if __name__ == "__main__":
    main()
