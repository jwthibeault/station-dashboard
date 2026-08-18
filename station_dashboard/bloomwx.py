class BloomWX:
    URL = "https://bloomwx.com/livedash/at/toano-va?zoom=8"
    LOAD_TIMEOUT = 20000

    def __init__(self, page):
        self.page = page

    def _is_loaded(self):
        if self.page.is_closed():
            return False

        if "bloomwx.com" not in self.page.url:
            return False

        try:
            text = self.page.locator("body").inner_text(timeout=5000)
            return "NEXT 12 HOURS" in text and "7-DAY FORECAST" in text
        except Exception:
            return False

    def _has_broken_map_image(self):
        if self.page.is_closed():
            return False

        try:
            return self.page.locator(
                'img[src*="server.arcgisonline.com"]'
            ).evaluate_all(
                """
                images => images.some(
                    img => img.complete && img.naturalWidth === 0
                )
                """
            )
        except Exception:
            return False

    def _wait_for_loaded(self):
        self.page.wait_for_function(
            """
            () => {
                const text = document.body
                    ? document.body.innerText
                    : "";

                return text.includes("NEXT 12 HOURS") &&
                       text.includes("7-DAY FORECAST");
            }
            """,
            timeout=self.LOAD_TIMEOUT
        )

    def open(self):
        print("Opening BloomWX...")

        try:
            self.page.goto(
                self.URL,
                wait_until="domcontentloaded",
                timeout=30000
            )

            self._wait_for_loaded()
            print("BloomWX loaded successfully.")
            return True

        except Exception as e:
            print(f"BloomWX did not finish loading: {e}")
            print("Refreshing BloomWX...")

            try:
                self.page.reload(
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                self._wait_for_loaded()
                print("BloomWX loaded successfully after refresh.")
                return True

            except Exception as e:
                print(f"BloomWX refresh failed: {e}")
                print("BloomWX will be retried during its next rotation.")
                return False

    def show(self):
        self.page.bring_to_front()

    def check(self):
        if not self._is_loaded():
            return False

        if self._has_broken_map_image():
            print("BloomWX map image failed to load.")
            print("Refreshing BloomWX...")

            try:
                self.page.reload(
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                self._wait_for_loaded()
                print("BloomWX loaded successfully after map refresh.")
                return True

            except Exception as e:
                print(f"BloomWX map refresh failed: {e}")
                print("BloomWX will be retried during its next rotation.")
                return False

        return True
