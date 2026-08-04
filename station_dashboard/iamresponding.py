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

        self.page.wait_for_load_state("networkidle")

    def show(self):
        self.page.bring_to_front()
