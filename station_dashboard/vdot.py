from playwright.sync_api import Page, TimeoutError


class VDOT:
    def __init__(self, page: Page, credentials: dict):
        self.page = page
        self.credentials = credentials

    def open(self):
        self.page.goto("https://secure.vdotcameras.com/auth/login")

        #
        # If the Username box appears, we need to log in.
        # Otherwise, VDOT has kept our session alive.
        #
        try:
            self.page.get_by_role(
                "textbox",
                name="Username"
            ).wait_for(timeout=3000)

            print("Login required.")

            self.page.get_by_role(
                "textbox",
                name="Username"
            ).fill(self.credentials["username"])

            self.page.get_by_role(
                "button",
                name="Next"
            ).click()

            self.page.get_by_role(
                "textbox",
                name="Password"
            ).fill(self.credentials["password"])

            self.page.get_by_role(
                "button",
                name="Next"
            ).click()

        except TimeoutError:
            print("Already logged into VDOT.")

        self.page.wait_for_load_state("networkidle")

        print("Opening camera wall...")

        self.page.get_by_role(
            "link",
            name="Wall"
        ).click()

        print("Waiting for Operator Application...")

        self.page.wait_for_selector(
            'iframe[title="Operator Application"]'
        )

        frame = self.page.frame_locator(
            'iframe[title="Operator Application"]'
        )

        print("Waiting for VDOT wall to initialize...")

        wall = frame.locator("div.wall.page")

        wall.wait_for(
            state="visible",
            timeout=15000
        )

        #
        # The Wall container becomes visible before the VDOT
        # application has finished initializing. Wait for the
        # actual loading overlay and loading messages to disappear
        # before attempting to interact with the wall.
        #
        print("Waiting for VDOT loading overlay...")

        loading_modal = frame.locator(
            "vp-modal-loading"
        )

        loading_modal.wait_for(
            state="hidden",
            timeout=15000
        )

        print("VDOT loading overlay cleared.")

        print("Waiting for VDOT loading messages...")

        loading_messages = frame.locator(
            ".loading-message"
        )

        loading_messages.first.wait_for(
            state="hidden",
            timeout=15000
        )

        print("VDOT loading messages cleared.")

        print("Waiting for Device Groups panel...")

        wall_open = frame.locator(
            "div.wall.page.device-groups-open"
        )

        wall_open.wait_for(
            state="visible",
            timeout=15000
        )

        print("Device Groups panel is open.")

        device_groups = frame.get_by_role(
            "button",
            name="Device Groups",
            exact=True
        )

        device_groups.wait_for(
            state="visible",
            timeout=5000
        )

        print("Closing Device Groups...")

        device_groups.click()

        print("Waiting for Device Groups panel to close...")

        views_open = False

        wall_closed = frame.locator(
            "div.wall.page:not(.device-groups-open)"
        )

        try:
            wall_closed.wait_for(
                state="visible",
                timeout=3000
            )

        except TimeoutError:
            print(
                "Device Groups did not close. "
                "Using VDOT panel refresh workaround..."
            )

            print("Opening Views...")

            frame.get_by_role(
                "button",
                name="Views",
                exact=True
            ).click()

            views_open = True

            print("Returning to Device Groups...")

            device_groups = frame.get_by_role(
                "button",
                name="Device Groups",
                exact=True
            )

            device_groups.wait_for(
                state="visible",
                timeout=5000
            )

            print("Closing Device Groups again...")

            device_groups.click()

            wall_closed.wait_for(
                state="visible",
                timeout=10000
            )

        print("Device Groups panel closed.")

        print("Opening Views...")

        if not views_open:
            frame.get_by_role(
                "button",
                name="Views",
                exact=True
            ).click()

        frame.get_by_role(
            "button",
            name="Personal"
        ).click()

        print("Selecting I-64 Toano...")

        frame.get_by_text(
            "I-64 Toano"
        ).click()

        print("Closing Views panel...")

        frame.get_by_role(
            "button",
            name="Close Widget Views"
        ).click()

        print("VDOT camera wall ready.")
        return True

    def show(self):
        self.page.bring_to_front()

    def check(self):
        """
        Returns True if VDOT is still displaying the operator wall.
        Returns False if we've been redirected elsewhere,
        the logout popup is visible, or the camera wall is not visible.
        """

        if not self.page.url.startswith(
            "https://secure.vdotcameras.com/operator/wall"
        ):
            return False

        if self.page.locator(
            "#logged-out-message"
        ).is_visible():
            return False

        try:
            frame = self.page.frame_locator(
                'iframe[title="Operator Application"]'
            )

            wall = frame.locator(
                "div.wall.page"
            )

            return wall.is_visible(timeout=2000)

        except Exception:
            return False
