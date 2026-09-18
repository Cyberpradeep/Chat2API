"""
Browser Context Manager using Playwright.
Provides persistent session management, anti-throttling flags, and stealth capabilities.
"""

import os
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page
from config.settings import settings
from config.logger import get_logger
from config import selectors

logger = get_logger("browser_manager")

class BrowserManager:
    def __init__(self, user_data_dir: str = settings.USER_DATA_DIR, headless: bool = settings.HEADLESS):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    @property
    def page(self) -> Optional[Page]:
        return self._page

    async def initialize(self) -> Page:
        """Launches the persistent Chromium context and opens ChatGPT."""
        if self._page and not self._page.is_closed():
            return self._page

        logger.info(f"Launching persistent browser context from {self.user_data_dir} (headless={self.headless})...")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self._playwright = await async_playwright().start()

        launch_kwargs = {
            "user_data_dir": self.user_data_dir,
            "headless": self.headless,
            "args": [
                # Anti-throttling flags (ensures full background speed)
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=CalculateNativeWinOcclusion",
                # Stealth flags
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--start-maximized"
            ],
            "viewport": None,
            "ignore_default_args": ["--enable-automation"]
        }

        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                channel=settings.BROWSER_CHANNEL,
                **launch_kwargs
            )
        except Exception:
            logger.info("Preferred browser channel unavailable, launching bundled Chromium...")
            self._context = await self._playwright.chromium.launch_persistent_context(
                **launch_kwargs
            )

        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()

        logger.info("Navigating to https://chatgpt.com ...")
        try:
            await self._page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning(f"Initial navigation reached timeout ({e}), continuing...")

        await asyncio.sleep(2)
        await self.dismiss_popups()
        logger.info("Browser manager ready.")
        return self._page

    async def dismiss_popups(self):
        """Dismisses any random release notes, cookie banners, or overlays."""
        if not self._page:
            return
        for sel in selectors.DISMISS_MODALS:
            try:
                btn = self._page.locator(sel).first
                if await btn.is_visible(timeout=400):
                    logger.info(f"Dismissing overlay: {sel}")
                    await btn.click(timeout=800)
                    await asyncio.sleep(0.3)
            except Exception:
                pass

    async def get_status(self) -> dict:
        """Returns readiness status."""
        is_ready = False
        url = None
        has_input = False
        if self._page and not self._page.is_closed():
            url = self._page.url
            for sel in selectors.PROMPT_INPUT:
                try:
                    if await self._page.locator(sel).first.is_visible(timeout=500):
                        has_input = True
                        break
                except Exception:
                    pass
            is_ready = ("chatgpt.com" in (url or "")) and has_input

        return {
            "browser_ready": is_ready,
            "current_url": url,
            "input_ready": has_input,
            "profile_dir": self.user_data_dir
        }

    async def close(self):
        """Clean shutdown."""
        logger.info("Closing browser manager...")
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._playwright = None
