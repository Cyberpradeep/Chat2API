"""
One-time Login Helper for ChatGPT API
Launches a visible Chromium window with a persistent user profile directory.
Log into your ChatGPT account once, and the session will be saved for the API server.
"""

import os
import sys
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")

def main():
    print("=" * 60)
    print("  ChatGPT One-Time Login Helper")
    print("=" * 60)
    print(f"Profile directory: {USER_DATA_DIR}")
    print("\nLaunching browser...")

    os.makedirs(USER_DATA_DIR, exist_ok=True)

    with sync_playwright() as p:
        # Launch persistent context with headed browser
        launch_kwargs = {
            "user_data_dir": USER_DATA_DIR,
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ],
            "viewport": None,
            "ignore_default_args": ["--enable-automation"]
        }
        
        try:
            context = p.chromium.launch_persistent_context(
                channel="chrome",
                **launch_kwargs
            )
        except Exception:
            # Fallback to Playwright's bundled Chromium
            context = p.chromium.launch_persistent_context(**launch_kwargs)

        page = context.pages[0] if context.pages else context.new_page()
        
        print("Navigating to https://chatgpt.com ...")
        try:
            page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Notice: Page navigation reached timeout ({e}), but browser is open.")

        print("\n" + "*" * 60)
        print(" ACTION REQUIRED:")
        print(" 1. In the browser window that just opened, log into ChatGPT.")
        print(" 2. Complete any Cloudflare check, CAPTCHA, or 2FA if prompted.")
        print(" 3. Verify that you see the normal ChatGPT prompt box.")
        print(" 4. Return to this console and press [ENTER] to save & exit.")
        print("*" * 60 + "\n")

        try:
            input("Press [Enter] after you have successfully logged in: ")
        except (KeyboardInterrupt, EOFError):
            pass

        print("Saving session data to user_data directory...")
        context.close()
        print("Session successfully saved! You can now start the API server with:")
        print("  python main.py")

if __name__ == "__main__":
    main()
