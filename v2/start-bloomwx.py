import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from playwright.sync_api import sync_playwright

from station_dashboard.bloomwx import BloomWX


def main():
    with sync_playwright() as p:
        print("Connecting to BloomWX Chromium on CDP port 9230...")

        browser = p.chromium.connect_over_cdp(
            "http://127.0.0.1:9230"
        )

        context = browser.contexts[0]

        pages = [
            page for page in context.pages
            if page.url.startswith("http")
        ]

        if not pages:
            raise RuntimeError("No HTTP page found in BloomWX Chromium.")

        page = pages[0]

        print(f"BloomWX page: {page.url}")

        bloomwx = BloomWX(page)

        print("Checking BloomWX...")
        healthy = bloomwx.check()

        print(f"BloomWX health check result: {healthy}")

        if not healthy:
            raise RuntimeError("BloomWX health check failed.")

        print("BloomWX health check passed.")

        input("Press Enter to disconnect from BloomWX...")


if __name__ == "__main__":
    main()
