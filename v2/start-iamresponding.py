import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright

from station_dashboard.iamresponding import IamResponding


def main():
    with open(BASE_DIR / "credentials.json") as f:
        credentials = json.load(f)

    with sync_playwright() as p:
        print("Connecting to IamResponding Chromium on CDP port 9232...")

        browser = p.chromium.connect_over_cdp(
            "http://127.0.0.1:9232"
        )

        context = browser.contexts[0]

        pages = [
            page for page in context.pages
            if page.url.startswith("http")
        ]

        if not pages:
            raise RuntimeError(
                "No HTTP page found in IamResponding Chromium."
            )

        page = pages[0]

        print(f"IamResponding page: {page.url}")

        iam = IamResponding(
            page,
            credentials["iamresponding"]
        )

        print("Opening IamResponding...")
        iam.open()

        print("Checking IamResponding...")
        healthy = iam.check()

        print(f"IamResponding health check result: {healthy}")

        if not healthy:
            raise RuntimeError(
                "IamResponding health check failed."
            )

        print("IamResponding health check passed.")

        input("Press Enter to disconnect from IamResponding...")


if __name__ == "__main__":
    main()
