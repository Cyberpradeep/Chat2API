"""
ChatGPT Automation Service using Playwright.
Manages persistent browser sessions, prompt submission, stream completion detection,
and response extraction with fallback selectors.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from markdownify import markdownify as md
from playwright.async_api import async_playwright, Playwright, BrowserContext, Page

logger = logging.getLogger("chatgpt_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

# Selector definitions with fallbacks
INPUT_SELECTORS = [
    "#prompt-textarea",
    'div[id="prompt-textarea"][contenteditable="true"]',
    'div[role="textbox"][aria-label*="ChatGPT"]',
    'div[role="textbox"]',
    'textarea#prompt-textarea'
]

SEND_SELECTORS = [
    'button[data-testid="send-button"]',
    'button[aria-label="Send prompt"]',
    'button[aria-label="Send message"]',
    'button[data-testid="composer-speech-button"]'
]

STOP_SELECTORS = [
    'button[data-testid="stop-button"]',
    'button[aria-label="Stop generating"]',
    'button[aria-label="Stop streaming"]'
]

ASSISTANT_SELECTORS = [
    'div[data-message-author-role="assistant"]',
    'article:has([data-message-author-role="assistant"])',
    '[data-testid^="conversation-turn-"]:has([data-message-author-role="assistant"])'
]

DISMISS_MODAL_SELECTORS = [
    'button[aria-label="Close"]',
    'button:has-text("Dismiss")',
    'button:has-text("Stay logged out")',
    'button:has-text("Okay, let\'s go")',
    'button:has-text("Accept all")',
    'button:has-text("Reject non-essential")'
]


class ChatGPTService:
    def __init__(self, user_data_dir: str = USER_DATA_DIR, headless: bool = HEADLESS):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initializes the browser context and opens ChatGPT."""
        if self._initialized and self._page and not self._page.is_closed():
            return

        logger.info("Initializing Playwright and launching persistent Chromium context...")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self._playwright = await async_playwright().start()

        launch_kwargs = {
            "user_data_dir": self.user_data_dir,
            "headless": self.headless,
            "args": [
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
                channel="chrome",
                **launch_kwargs
            )
        except Exception:
            logger.info("Chrome channel not found, falling back to bundled Chromium...")
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
        await self._dismiss_popups()
        self._initialized = True
        logger.info("ChatGPT service successfully initialized!")

    async def _dismiss_popups(self):
        """Dismisses any random welcome popups, cookie consent banners, or alerts."""
        if not self._page:
            return
        for selector in DISMISS_MODAL_SELECTORS:
            try:
                btn = self._page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    logger.info(f"Dismissing modal via selector: {selector}")
                    await btn.click(timeout=1000)
                    await asyncio.sleep(0.5)
            except Exception:
                pass

    async def new_chat(self):
        """Navigates to a clean new chat session."""
        async with self._lock:
            if not self._page:
                await self.initialize()
            logger.info("Resetting conversation: navigating to https://chatgpt.com/ ...")
            await self._page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(1.5)
            await self._dismiss_popups()

    async def send_prompt(self, prompt: str, new_chat: bool = False, timeout_seconds: int = 120) -> Dict[str, Any]:
        """
        Sends a prompt to ChatGPT, waits for completion, and returns the response.
        """
        async with self._lock:
            if not self._initialized or not self._page or self._page.is_closed():
                await self.initialize()

            if new_chat:
                logger.info("Starting fresh conversation before sending prompt...")
                await self._page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(1.5)

            await self._dismiss_popups()

            # 1. Find the input container
            prompt_locator = None
            for sel in INPUT_SELECTORS:
                loc = self._page.locator(sel).first
                try:
                    if await loc.is_visible(timeout=2000):
                        prompt_locator = loc
                        break
                except Exception:
                    continue

            if not prompt_locator:
                # Page may need a refresh or re-navigation
                logger.warning("Prompt input box not immediately found. Re-navigating to chatgpt.com...")
                await self._page.goto("https://chatgpt.com/", wait_until="networkidle", timeout=45000)
                await asyncio.sleep(2)
                for sel in INPUT_SELECTORS:
                    loc = self._page.locator(sel).first
                    try:
                        if await loc.is_visible(timeout=3000):
                            prompt_locator = loc
                            break
                    except Exception:
                        continue

            if not prompt_locator:
                raise RuntimeError(
                    "Could not locate the prompt input box on chatgpt.com. "
                    "Make sure you are logged in using `python login_helper.py`."
                )

            # 2. Count existing assistant responses
            initial_count = await self._get_assistant_turn_count()

            # 3. Enter prompt text
            logger.info("Focusing input and entering prompt...")
            await prompt_locator.click()
            await asyncio.sleep(0.2)

            # Use fill, or keyboard insertion for contenteditable
            try:
                await prompt_locator.fill(prompt)
            except Exception:
                await self._page.keyboard.press("Control+A")
                await self._page.keyboard.press("Backspace")
                await self._page.keyboard.insert_text(prompt)

            await asyncio.sleep(0.5)

            # 4. Click send or press Enter
            sent = False
            for sel in SEND_SELECTORS:
                btn = self._page.locator(sel).first
                try:
                    if await btn.is_visible(timeout=1000) and await btn.is_enabled(timeout=1000):
                        # Avoid clicking speech button if send button isn't ready
                        if "speech" in sel:
                            continue
                        logger.info(f"Clicking send button: {sel}")
                        await btn.click()
                        sent = True
                        break
                except Exception:
                    continue

            if not sent:
                logger.info("Send button not directly clickable, pressing Enter key...")
                await prompt_locator.press("Enter")

            # 5. Wait for streaming response to start and complete
            logger.info("Waiting for generation to finish...")
            response_text = await self._wait_for_completion(initial_count, timeout_seconds)

            return {
                "prompt": prompt,
                "response": response_text,
                "status": "success"
            }

    async def _get_assistant_turn_count(self) -> int:
        """Counts how many assistant message turns currently exist on the page."""
        for sel in ASSISTANT_SELECTORS:
            try:
                count = await self._page.locator(sel).count()
                if count > 0:
                    return count
            except Exception:
                continue
        return 0

    async def _wait_for_completion(self, previous_count: int, timeout_seconds: int) -> str:
        """
        Polls until:
        1. A new assistant turn appears (or existing updates).
        2. Generation completes (stop button disappears and text stabilizes).
        """
        start_time = asyncio.get_event_loop().time()
        
        # Phase 1: Wait for generation indicator or new turn
        generation_started = False
        while (asyncio.get_event_loop().time() - start_time) < 15:
            # Check for stop button
            for stop_sel in STOP_SELECTORS:
                try:
                    if await self._page.locator(stop_sel).first.is_visible(timeout=200):
                        generation_started = True
                        break
                except Exception:
                    pass
            if generation_started:
                break

            current_count = await self._get_assistant_turn_count()
            if current_count > previous_count:
                generation_started = True
                break

            await asyncio.sleep(0.3)

        logger.info(f"Generation activity detected: {generation_started}")

        # Phase 2: Wait until stop button disappears and text length stabilizes
        last_text = ""
        stable_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            # Check if stop button is still present
            is_still_generating = False
            for stop_sel in STOP_SELECTORS:
                try:
                    if await self._page.locator(stop_sel).first.is_visible(timeout=200):
                        is_still_generating = True
                        break
                except Exception:
                    pass

            current_text = await self._extract_latest_response()

            if not is_still_generating and len(current_text) > 0:
                if current_text == last_text:
                    stable_count += 1
                    if stable_count >= 3:  # Text unchanged for ~1.5s after stop button detached
                        logger.info("Response generation confirmed complete.")
                        return current_text
                else:
                    stable_count = 0
            
            last_text = current_text
            await asyncio.sleep(0.5)

        if last_text:
            logger.warning("Timeout reached, returning last captured text.")
            return last_text

        raise TimeoutError(f"Generation timed out after {timeout_seconds} seconds with no output.")

    async def _extract_latest_response(self) -> str:
        """Extracts and formats text from the last assistant message turn."""
        for sel in ASSISTANT_SELECTORS:
            try:
                locator = self._page.locator(sel)
                count = await locator.count()
                if count > 0:
                    last_elem = locator.nth(count - 1)
                    # Check for prose / markdown container
                    prose_elem = last_elem.locator(".markdown, .prose, div.prose").first
                    if await prose_elem.is_visible(timeout=300):
                        html_content = await prose_elem.inner_html()
                        # Convert HTML to markdown for clean structure
                        clean_md = md(html_content, strip=["button"]).strip()
                        if clean_md:
                            return clean_md
                    # Fallback to plain inner_text
                    text = (await last_elem.inner_text()).strip()
                    if text:
                        return text
            except Exception:
                continue
        return ""

    async def get_status(self) -> Dict[str, Any]:
        """Returns the readiness status of the browser and ChatGPT page."""
        is_ready = False
        url = None
        has_input = False
        if self._initialized and self._page and not self._page.is_closed():
            url = self._page.url
            for sel in INPUT_SELECTORS:
                try:
                    if await self._page.locator(sel).first.is_visible(timeout=500):
                        has_input = True
                        break
                except Exception:
                    pass
            is_ready = ("chatgpt.com" in url) and has_input

        return {
            "initialized": self._initialized,
            "browser_ready": is_ready,
            "current_url": url,
            "input_ready": has_input,
            "profile_dir": self.user_data_dir
        }

    async def close(self):
        """Clean shutdown of browser and context."""
        logger.info("Closing ChatGPT service...")
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False
        logger.info("ChatGPT service closed.")
