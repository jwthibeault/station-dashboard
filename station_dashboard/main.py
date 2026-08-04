import time

from browser import Browser
from config import Config
from iamresponding import IamResponding
from vdot import VDOT


def main():
    config = Config()

    browser = Browser()

    print("Connecting to Chromium...")
    browser.connect()
    print("Connected successfully.")

    #
    # Create dashboard modules
    #
    iam = IamResponding(
        browser.new_page(),
        config.credentials["iamresponding"]
    )

    vdot = VDOT(
        browser.new_page(),
        config.credentials["vdot"]
    )

    dashboards = [
        iam,
        vdot
    ]

    #
    # Open each dashboard
    #
    print("Opening IamResponding...")
    iam.open()

    print("Opening VDOT...")
    vdot.open()

    print()
    print("Dashboard is running.")
    print(f"Rotating every {config.rotation_seconds} seconds.")

    while True:
        for dashboard in dashboards:
            dashboard.show()
            time.sleep(config.rotation_seconds)


if __name__ == "__main__":
    main()
