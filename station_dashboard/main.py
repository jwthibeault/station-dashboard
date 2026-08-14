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
        ("IamResponding", iam, config.rotation_seconds("IamResponding")),
        ("VDOT", vdot, config.rotation_seconds("VDOT Cameras"))
    ]

    #
    # Exclude dashboards configured with 0 seconds from the rotation.
    #
    active_dashboards = [
        (name, dashboard, seconds)
        for name, dashboard, seconds in dashboards
        if seconds > 0
    ]

    #
    # Track whether VDOT successfully initialized.
    #
    vdot_ready = False

    #
    # Open IamResponding.
    #
    print("Opening IamResponding...")
    iam.open()

    #
    # Attempt to open VDOT.
    #
    # VDOT is allowed to fail during startup. If it does, the dashboard
    # continues running and VDOT will be retried during its next rotation.
    #
    print("Opening VDOT...")

    try:
        vdot.open()
        vdot_ready = True
        print("VDOT initialized successfully.")

    except Exception as e:
        print(f"VDOT startup failed: {e}")
        print("Continuing without VDOT for now.")
        print("VDOT will be retried during its next rotation.")

    print()
    print("Dashboard is running.")
    print("Rotation:")
    for name, _, seconds in active_dashboards:
        print(f"  {name}: {seconds} seconds")

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

        for name, dashboard, seconds in active_dashboards:

            #
            # VDOT may have failed during startup or during a previous
            # rotation. Give it another opportunity when its turn comes.
            #
            if name == "VDOT" and not vdot_ready:

                print("Retrying VDOT...")

                #
                # Show VDOT before attempting the retry so that, if the
                # initialization fails, the current VDOT state remains
                # visible for the remainder of its rotation period.
                #
                dashboard.show()

                try:
                    dashboard.open()
                    vdot_ready = True
                    print("VDOT initialized successfully.")

                except Exception as e:
                    print(f"VDOT retry failed: {e}")
                    print("Leaving VDOT visible for this rotation.")
                    wait_for_rotation(seconds)
                    continue

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

                #
                # VDOT failures are non-fatal. If reconnecting VDOT fails,
                # mark it unavailable and continue the rotation.
                #
                if name == "VDOT":

                    try:
                        dashboard.open()
                        vdot_ready = True
                        print("VDOT reconnected successfully.")

                    except Exception as e:
                        vdot_ready = False
                        print(f"VDOT reconnect failed: {e}")
                        print("Skipping VDOT this rotation.")
                        continue

                else:

                    #
                    # Other dashboards retain their existing behavior.
                    #
                    dashboard.open()

                #
                # Make sure the recovered dashboard is visible.
                #
                dashboard.show()

            #
            # Display the dashboard for its configured rotation time
            # while continuing to monitor for an IaR emergency.
            #
            wait_for_rotation(seconds)


if __name__ == "__main__":
    main()
