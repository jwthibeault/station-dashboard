import json
import time

from playwright.sync_api import Page, TimeoutError


HEARTBEAT_TIMEOUT_SECONDS = 60


class IamResponding:
    def __init__(self, page: Page, credentials: dict):
        self.page = page
        self.credentials = credentials
        self._last_heartbeat = None
        self._heartbeat_monitor_started_at = time.monotonic()
        self._heartbeat_failure_detected = False
        self._last_failure_reason = None

        self._cdp_session = self.page.context.new_cdp_session(
            self.page
        )
        self._cdp_session.send("Network.enable")
        self._cdp_session.on(
            "Network.webSocketFrameReceived",
            self._record_heartbeat,
        )

        print("IamResponding HubSignalR heartbeat monitoring active.")

    def _record_heartbeat(self, event):
        try:
            payload = event["response"]["payloadData"]

            for message in payload.split("\x1e"):
                if json.loads(message).get("type") == 6:
                    self._last_heartbeat = time.monotonic()

        except (KeyError, TypeError, ValueError):
            pass

    def _heartbeat_timed_out(self):
        last_heartbeat = (
            self._last_heartbeat
            or self._heartbeat_monitor_started_at
        )

        return (
            time.monotonic() - last_heartbeat
            >= HEARTBEAT_TIMEOUT_SECONDS
        )

    def open(self):
        self._last_heartbeat = None
        self._heartbeat_monitor_started_at = time.monotonic()

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
        return True

    def show(self):
        self.page.bring_to_front()

    def check(self):
        self._heartbeat_failure_detected = False
        self._last_failure_reason = None

        if not self.page.url.startswith(
            "https://dashboard.iamresponding.com"
        ):
            self._last_failure_reason = "page_url_validation_failed"
            return False

        try:
            text = self.page.locator(
                "body"
            ).inner_text(timeout=5000).lower()

            if "trying to re-establish connection to the server" in text:
                self._last_failure_reason = "visible_server_connection_error"
                print(
                    "IamResponding server connection error banner detected."
                )
                return False

            if self._heartbeat_timed_out():
                self._heartbeat_failure_detected = True
                self._last_failure_reason = "signalr_heartbeat_timeout"
                print(
                    "IamResponding HubSignalR heartbeat has not been "
                    f"detected for {HEARTBEAT_TIMEOUT_SECONDS} seconds."
                )
                return False

        except Exception:
            self._last_failure_reason = "page_validation_failed"
            return False

        return True

    def heartbeat_failure_detected(self):
        return self._heartbeat_failure_detected

    def health_failure_reason(self):
        return self._last_failure_reason

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
