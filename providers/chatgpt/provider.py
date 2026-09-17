"""
ChatGPT Provider Implementation.
Coordinates browser lifecycle, feature toggles (Think, Web Search, Deep Research),
file attachments, and response extraction.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from providers.base_provider import BaseProvider
from core.browser_manager import BrowserManager
from core.file_uploader import FileUploader
from config import selectors
from . import toggles
from . import extractor

logger = logging.getLogger("chatgpt_provider")

class ChatGPTProvider(BaseProvider):
    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser_mgr = browser_manager or BrowserManager()
        self.file_uploader = FileUploader()

    async def initialize(self) -> None:
        """Initializes the persistent browser context and navigates to ChatGPT."""
        await self.browser_mgr.initialize()

    async def is_ready(self) -> Dict[str, Any]:
        """Returns browser and interface status."""
        return await self.browser_mgr.get_status()

    async def new_chat(self) -> None:
        """Navigates to a fresh chat window."""
        async with self.browser_mgr.lock:
            page = await self.browser_mgr.initialize()
            logger.info("Starting a new conversation session...")
            await page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(1.5)
            await self.browser_mgr.dismiss_popups()

    async def send_prompt(
        self,
        prompt: str,
        think: bool = False,
        web_search: bool = False,
        deep_research: bool = False,
        files: Optional[List[str]] = None,
        new_chat: bool = False,
        timeout_seconds: int = 180
    ) -> Dict[str, Any]:
        """
        Sends prompt with selected toggles and file attachments.
        """
        async with self.browser_mgr.lock:
            page = await self.browser_mgr.initialize()

            if new_chat:
                logger.info("Resetting conversation before sending prompt...")
                await page.goto("https://chatgpt.com/", wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(1.5)

            await self.browser_mgr.dismiss_popups()

            # 1. Apply feature toggles
            if think:
                await toggles.set_think_mode(page, True)
            if web_search:
                await toggles.set_web_search(page, True)
            elif deep_research:
                await toggles.set_deep_research(page, True)

            # 2. Attach any files or images
            if files:
                await self.file_uploader.attach_files(page, files)

            # 3. Locate prompt input box
            prompt_locator = None
            for sel in selectors.PROMPT_INPUT:
                loc = page.locator(sel).first
                try:
                    if await loc.is_visible(timeout=2000):
                        prompt_locator = loc
                        break
                except Exception:
                    continue

            if not prompt_locator:
                logger.warning("Prompt box not visible. Re-navigating to chatgpt.com...")
                await page.goto("https://chatgpt.com/", wait_until="networkidle", timeout=45000)
                await asyncio.sleep(2)
                for sel in selectors.PROMPT_INPUT:
                    loc = page.locator(sel).first
                    try:
                        if await loc.is_visible(timeout=3000):
                            prompt_locator = loc
                            break
                    except Exception:
                        continue

            if not prompt_locator:
                raise RuntimeError("Could not find prompt input on chatgpt.com. Ensure you are logged in.")

            # 4. Count existing turns before typing
            initial_count = await extractor.get_assistant_turn_count(page)

            # 5. Type prompt
            logger.info("Typing prompt into composer...")
            await prompt_locator.click()
            await asyncio.sleep(0.2)

            try:
                await prompt_locator.fill(prompt)
            except Exception:
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.insert_text(prompt)

            await asyncio.sleep(0.5)

            # 6. Click send
            sent = False
            for sel in selectors.SEND_BUTTON:
                btn = page.locator(sel).first
                try:
                    if await btn.is_visible(timeout=1000) and await btn.is_enabled(timeout=1000):
                        logger.info(f"Clicking send button: {sel}")
                        await btn.click()
                        sent = True
                        break
                except Exception:
                    continue

            if not sent:
                logger.info("Clicking fallback: pressing Enter...")
                await prompt_locator.press("Enter")

            # 7. Wait for completion and extract response
            logger.info("Waiting for generation to finish...")
            extracted = await extractor.wait_for_completion(page, initial_count, timeout_seconds)

            return {
                "prompt": prompt,
                "response": extracted["content"],
                "thought_process": extracted.get("thought_process"),
                "sources": extracted.get("sources", []),
                "toggles": {
                    "think": think,
                    "web_search": web_search,
                    "deep_research": deep_research,
                    "files_count": len(files) if files else 0
                },
                "status": "success"
            }

    async def close(self) -> None:
        """Shuts down browser context."""
        await self.browser_mgr.close()
