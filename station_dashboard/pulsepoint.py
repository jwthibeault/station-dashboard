from playwright.sync_api import Page, TimeoutError
import time


class PulsePoint:
    def __init__(self, page: Page, credentials: dict | None = None):
        self.page = page
        self.credentials = credentials or {}
        self._rapid_polling_seen = False
        self._last_api_start = None

    def open(self):
        print("Opening PulsePoint...")

        self.page.goto("https://ppc.pulsepoint.org/")

        #
        # PulsePoint uses a Cognito login page.  Because the
        # Chromium profile is persistent, an existing session
        # should normally take us directly into PulsePoint.
        #
        try:
            username = self.page.locator("#signInFormUsername:visible").first

            username.wait_for(
                state="visible",
                timeout=5000
            )

            print("PulsePoint login required.")

            if not self.credentials.get("username"):
                raise RuntimeError(
                    "PulsePoint login is required, but no "
                    "PulsePoint username is configured."
                )

            if not self.credentials.get("password"):
                raise RuntimeError(
                    "PulsePoint login is required, but no "
                    "PulsePoint password is configured."
                )

            username.fill(
                self.credentials["username"]
            )

            self.page.locator(
                "#signInFormPassword:visible"
            ).first.fill(
                self.credentials["password"]
            )

            submit = self.page.locator("input[name='signInSubmitButton']:visible").first
            submit.wait_for(state="visible", timeout=15000)
            submit.click()
            print("PulsePoint Sign In button clicked.")

            print("PulsePoint login submitted.")

        except TimeoutError:
            if "auth.us-west-2.amazoncognito.com/login" in self.page.url:
                raise RuntimeError("PulsePoint login page detected, but login form was not ready.")
            print("PulsePoint session already active.")

        #
        # Wait for the application itself to become available.
        # Incident Admin is the first reliable application-level
        # element we have verified.
        #
        print("Waiting for PulsePoint application...")

        incident_admin = self.page.get_by_text(
            "Incident Admin",
            exact=True
        )

        incident_admin.wait_for(
            state="visible",
            timeout=30000
        )

        print("PulsePoint application ready.")

        #
        # Enter Incident Admin.
        #
        print("Opening Incident Admin...")

        incident_admin.click()

        #
        # Wait for the More Menu before continuing.
        #
        more_menu = self.page.get_by_role(
            "button",
            name="More Menu"
        )

        more_menu.wait_for(
            state="visible",
            timeout=30000
        )

        print("Incident Admin screen ready.")

        #
        # Hide Recent Incidents.
        #
        print("Hiding Recent Incidents...")

        more_menu.click()

        self.page.get_by_role(
            "menuitem",
            name="Hide Recent Incidents"
        ).click()

        #
        # The menu closes after the first selection, so reopen it.
        #
        print("Hiding PulsePoint header...")

        more_menu.click()

        self.page.get_by_role(
            "menuitem",
            name="Hide Header"
        ).click()

        print("PulsePoint display configuration complete.")

        return True

    def show(self):
        self.page.bring_to_front()

    def check(self):
        #
        # PulsePoint health is based on the incident API actually
        # polling.  A page can remain visually alive while API polling
        # has stopped, so the page/title alone is not sufficient.
        #
        # Diagnostic output reports:
        #   - time since the most recent incident API request
        #   - interval between the two most recent requests
        #   - whether rapid (~1.5-2.5 sec) polling has been observed
        #
        # If no incident API request has occurred for 90 seconds,
        # report the page unhealthy so the existing recovery system
        # reinitializes PulsePoint.
        #
        try:
            diagnostics = self.page.evaluate("""
                () => {
                    const entries = performance.getEntriesByType('resource')
                        .filter(e =>
                            /api\\.pulsepoint\\.org\\/v1\\/webapp\\?resource=incidents/i.test(e.name)
                        );

                    if (!entries.length) {
                        return {
                            count: 0,
                            lastAge: null,
                            latestInterval: null,
                            rapid: false
                        };
                    }

                    const now = performance.now();
                    const last = entries[entries.length - 1];

                    let latestInterval = null;
                    let rapid = false;

                      if (entries.length >= 2) {
                          const previous = entries[entries.length - 2];
                          latestInterval = last.startTime - previous.startTime;

                          const recent = entries.slice(-5);

                          rapid = recent.slice(1).some((entry, i) => {
                              const interval =
                                  entry.startTime - recent[i].startTime;
                              return interval >= 1000 && interval <= 2500;
                          });
                      }

                    return {
                        count: entries.length,
                        lastAge: now - last.startTime,
                        latestInterval,
                        rapid
                    };
                }
            """)

            if diagnostics["count"] == 0:
                print(
                    "PulsePoint API polling: no incident API requests observed."
                )
                return False

            age = diagnostics["lastAge"] / 1000
            interval = diagnostics["latestInterval"]

            if interval is not None:
                interval_seconds = interval / 1000
                print(
                    f"PulsePoint API polling: last request "
                    f"{age:.1f}s ago; latest interval "
                    f"{interval_seconds:.1f}s."
                )
            else:
                print(
                    f"PulsePoint API polling: last request "
                    f"{age:.1f}s ago; waiting for second request."
                )

            if diagnostics["rapid"]:
                self._rapid_polling_seen = True
                print(
                    "PulsePoint API polling: rapid polling pattern "
                    "(~1.5-2.5s) observed."
                )

            if age >= 90:
                print(
                    f"PulsePoint API polling STALE: no incident API "
                    f"request for {age:.1f}s; reinitializing PulsePoint."
                )
                return False

        except Exception as exc:
            print(f"PulsePoint API polling check error: {exc}")
            return False

        try:
            self.page.get_by_text(
                "Incident Admin",
                exact=True
            ).wait_for(
                state="attached",
                timeout=5000
            )
        except TimeoutError:
            #
            # Incident Admin may be hidden after the header is removed.
            # The API polling check above remains the primary heartbeat.
            #
            try:
                title = self.page.title()

                if title != "PulsePoint Central":
                    return False

                if self.page.is_closed():
                    return False

            except Exception:
                return False

        return True
