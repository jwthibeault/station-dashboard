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

        self.page.wait_for_timeout(1000)

        print("Opening Device Groups...")

        frame.get_by_role(
            "button",
            name="Device Groups"
        ).click()

        print("Opening Views...")

        frame.get_by_role(
            "button",
            name="Views"
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

    def show(self):
        self.page.bring_to_front()

    def check(self):
        """
        Returns True if VDOT is still displaying the operator wall.
        Returns False if we've been redirected elsewhere.
        """

        return self.page.url.startswith(
            "https://secure.vdotcameras.com/operator/wall"
        )
