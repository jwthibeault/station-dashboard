from playwright.sync_api import Page, TimeoutError


class IamResponding:
    def __init__(self, page: Page, credentials: dict):
        self.page = page
        self.credentials = credentials

    def open(self):
        self.page.goto("https://dashboard.iamresponding.com")

        try:
            self.page.get_by_role(
                "textbox",
                name="Agency Login Name"
            ).wait_for(timeout=3000)

            print("Login required.")

            self.page.get_by_role(
                "textbox",
                name="Agency Login Name"
            ).fill(self.credentials["agency"])

            self.page.get_by_role(
                "textbox",
                name="Username"
            ).fill(self.credentials["username"])

            self.page.get_by_role(
                "textbox",
                name="Password"
            ).fill(self.credentials["password"])

            self.page.get_by_role(
                "button",
                name="Log in"
            ).click()

            print("Login submitted.")

        except TimeoutError:
            print("Already logged into IamResponding.")

        #
        # Wait until the page is loaded enough to continue.
        # Using DOMContentLoaded is more reliable than waiting
        # for network activity to completely stop.
        #
        self.page.wait_for_load_state("domcontentloaded")

    def show(self):
        self.page.bring_to_front()

    def check(self):
        return self.page.url.startswith(
            "https://dashboard.iamresponding.com"
        )

    def is_emergency(self):
        return self.page.locator(
            'span[class*="_timer_"]'
        ).is_visible()

    def activate_emergency(self):
        print("IamResponding emergency detected.")
        print("Loading Hybrid map...")

        self.page.get_by_role(
            "button",
            name="GO!"
        ).nth(1).click()

        print("Zooming Hybrid map out one level...")

        try:
            self.page.get_by_role(
                "button",
                name="Zoom out"
            ).nth(1).click()

            print("Hybrid emergency map ready.")

        except TimeoutError:
            print("Hybrid map Zoom Out button was not available.")

        return True
