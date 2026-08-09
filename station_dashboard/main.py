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
    # Reuse the first two browser tabs instead of always creating new ones.
    #
    iam = IamResponding(
        browser.page(0),
        config.credentials["iamresponding"]
    )

    vdot = VDOT(
        browser.page(1),
        config.credentials["vdot"]
    )

    dashboards = [
        ("IamResponding", iam),
        ("VDOT", vdot)
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

    #
    # Wait for the rotation period while monitoring IamResponding
    # for emergency mode.
    #
    def wait_for_rotation(seconds):
        end_time = time.time() + seconds

        while time.time() < end_time:

            #
            # Check IamResponding for emergency mode.
            #
            if iam.is_emergency():

                print("IamResponding emergency detected.")

                #
                # Bring IamResponding to the front and activate
                # the Hybrid emergency map.
                #
                iam.show()
                iam.activate_emergency()

                print("Pausing dashboard rotation.")

                #
                # Stay on IamResponding until the emergency timer
                # disappears.
                #
                while iam.is_emergency():
                    time.sleep(1)

                print("IamResponding emergency ended.")
                print("Resuming dashboard rotation.")

            time.sleep(1)

    while True:

        for name, dashboard in dashboards:

            #
            # Bring the tab to the front first so Chromium updates it.
            #
            dashboard.show()

            #
            # Give the page a brief moment to process any redirects or
            # session changes that occurred while it was in the background.
            #
            time.sleep(0.5)

            #
            # Now verify that it's still healthy.
            #
            if not dashboard.check():

                print(f"{name} is no longer available.")
                print(f"Reconnecting {name}...")

                dashboard.open()

                #
                # Make sure the recovered dashboard is visible.
                #
                dashboard.show()

            #
            # Display the dashboard for the configured rotation time
            # while continuing to monitor for an IaR emergency.
            #
            wait_for_rotation(config.rotation_seconds)


if __name__ == "__main__":
    main()
