import json
import time

from playwright.sync_api import Page, TimeoutError


HEARTBEAT_TIMEOUT_SECONDS = 60

HUB_SIGNALR = "HubSignalR"
GLOBAL_HUB = "Global"


class IamResponding:
    def __init__(self, page: Page, credentials: dict):
        self.page = page
        self.credentials = credentials
        self._socket_names = {}
        self._active_sockets = set()
        self._last_heartbeats = {
            HUB_SIGNALR: None,
            GLOBAL_HUB: None,
        }
        self._last_hub_update = None
        self._heartbeat_monitor_started_at = time.monotonic()
        self._heartbeat_failure_detected = False
        self._last_failure_reason = None

        self._cdp_session = self.page.context.new_cdp_session(
            self.page
        )
        self._cdp_session.send("Network.enable")
        self._cdp_session.on(
            "Network.webSocketCreated",
            self._record_websocket_created,
        )
        self._cdp_session.on(
            "Network.webSocketClosed",
            self._record_websocket_closed,
        )
        self._cdp_session.on(
            "Network.webSocketFrameReceived",
            self._record_heartbeat,
        )

        print("IamResponding SignalR monitoring active.")

    @staticmethod
    def _socket_name(url):
        normalized_url = url.lower()

        if "/hubsignalr" in normalized_url:
            return HUB_SIGNALR

        if "/globalhub" in normalized_url:
            return GLOBAL_HUB

        return None

    def _reset_signalr_state(self):
        self._socket_names = {}
        self._active_sockets = set()
        self._last_heartbeats = {
            HUB_SIGNALR: None,
            GLOBAL_HUB: None,
        }
        self._last_hub_update = None
        self._heartbeat_monitor_started_at = time.monotonic()

    def _record_websocket_created(self, event):
        socket_name = self._socket_name(event.get("url", ""))

        if socket_name is None:
            return

        request_id = event["requestId"]
        self._socket_names[request_id] = socket_name
        self._active_sockets.add(request_id)

        print(f"IamResponding SignalR connected: {socket_name}.")

    def _record_websocket_closed(self, event):
        request_id = event["requestId"]
        socket_name = self._socket_names.get(request_id)

        if socket_name is None:
            return

        self._active_sockets.discard(request_id)
        print(f"IamResponding SignalR closed: {socket_name}.")

    def _record_heartbeat(self, event):
        try:
            socket_name = self._socket_names.get(event["requestId"])

            if socket_name is None:
                return

            payload = event["response"]["payloadData"]

            for message in payload.split("\x1e"):
                if not message:
                    continue

                try:
                    signalr_message = json.loads(message)
                except (TypeError, ValueError):
                    continue

                if signalr_message.get("type") == 6:
                    self._last_heartbeats[socket_name] = (
                        time.monotonic()
                    )

                elif (
                    socket_name == HUB_SIGNALR
                    and signalr_message.get("type") == 1
                ):
                    target = signalr_message.get("target", "unknown")
                    self._last_hub_update = time.monotonic()
                    print(
                        "IamResponding HubSignalR update received: "
                        f"target={target}."
                    )

        except (KeyError, TypeError, ValueError):
            pass

    def _heartbeat_timed_out(self):
        last_heartbeat = (
            self._last_heartbeats[HUB_SIGNALR]
            or self._heartbeat_monitor_started_at
        )

        return (
            time.monotonic() - last_heartbeat
            >= HEARTBEAT_TIMEOUT_SECONDS
        )

    def open(self):
        self._reset_signalr_state()

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

    def establish_signalr_monitoring(self):
        """Reload once so this monitor observes and names both hubs."""
        self._reset_signalr_state()
        print(
            "IamResponding refreshing once to establish "
            "SignalR monitoring."
        )
        self.page.reload(wait_until="domcontentloaded")

    @staticmethod
    def _age_text(timestamp):
        if timestamp is None:
            return "not observed"

        return f"{int(time.monotonic() - timestamp)}s"

    def log_signalr_status(self):
        hub_connected = any(
            self._socket_names.get(request_id) == HUB_SIGNALR
            for request_id in self._active_sockets
        )

        hub_status = "connected" if hub_connected else "not connected"
        print(
            "IamResponding SignalR status: "
            f"HubSignalR heartbeat age="
            f"{self._age_text(self._last_heartbeats[HUB_SIGNALR])}; "
            f"Global heartbeat age="
            f"{self._age_text(self._last_heartbeats[GLOBAL_HUB])}; "
            f"HubSignalR update age="
            f"{self._age_text(self._last_hub_update)}; "
            f"HubSignalR={hub_status}."
        )

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

            self.log_signalr_status()

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
