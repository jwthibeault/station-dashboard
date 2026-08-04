from playwright.sync_api import sync_playwright


class Browser:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    def connect(self):

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.connect_over_cdp(
            "http://127.0.0.1:9222"
        )

        # Reuse the existing browser context if one already exists.
        if self.browser.contexts:
            self.context = self.browser.contexts[0]
        else:
            self.context = self.browser.new_context(
                ignore_https_errors=True
            )

            # Disable Chromium credential prompts in new contexts.
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'credentials', {
                    value: undefined
                });
            """)

    def page(self, index=0):
        while len(self.context.pages) <= index:
            self.context.new_page()

        return self.context.pages[index]

    def new_page(self):
        return self.context.new_page()

    def close(self):
        if self.playwright:
            self.playwright.stop()
