"""
ChatGPT Feature Toggles Controller.
Controls the inline Think button and the '+' menu items (Web search, Deep research).
"""

import asyncio
from playwright.async_api import Page
from config import selectors
from config.logger import get_logger

logger = get_logger("chatgpt_toggles")

async def set_think_mode(page: Page, enable: bool):
    """
    Toggles the Think button on the prompt bar.
    """
    try:
        think_btn = None
        for sel in selectors.THINK_BUTTON:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1000):
                think_btn = btn
                break

        if not think_btn:
            logger.info("Think button not found on prompt bar, skipping.")
            return

        # Determine if currently active
        aria_pressed = await think_btn.get_attribute("aria-pressed")
        class_name = (await think_btn.get_attribute("class")) or ""
        # Often active buttons have aria-pressed="true" or background highlight class
        is_active = (aria_pressed == "true") or ("bg-" in class_name and "active" in class_name)

        if enable and not is_active:
            logger.info("Activating Think mode...")
            await think_btn.click()
            await asyncio.sleep(0.4)
        elif not enable and is_active:
            logger.info("Deactivating Think mode...")
            await think_btn.click()
            await asyncio.sleep(0.4)
    except Exception as e:
        logger.warning(f"Error adjusting Think toggle: {e}")


async def open_plus_menu(page: Page) -> bool:
    """Clicks the '+' button to reveal the tools menu."""
    for sel in selectors.PLUS_BUTTON:
        btn = page.locator(sel).first
        try:
            if await btn.is_visible(timeout=800):
                await btn.click()
                await asyncio.sleep(0.5)
                return True
        except Exception:
            continue
    return False


async def set_web_search(page: Page, enable: bool):
    """Enables Web search from the '+' popup menu."""
    if not enable:
        return
    logger.info("Enabling Web search via '+' menu...")
    if await open_plus_menu(page):
        for sel in selectors.WEB_SEARCH_ITEM:
            item = page.locator(sel).first
            try:
                if await item.is_visible(timeout=1500):
                    await item.click()
                    await asyncio.sleep(0.5)
                    logger.info("Web search enabled.")
                    return
            except Exception:
                continue
        logger.warning("Could not find Web search menu item.")


async def set_deep_research(page: Page, enable: bool):
    """Enables Deep research from the '+' popup menu."""
    if not enable:
        return
    logger.info("Enabling Deep research via '+' menu...")
    if await open_plus_menu(page):
        for sel in selectors.DEEP_RESEARCH_ITEM:
            item = page.locator(sel).first
            try:
                if await item.is_visible(timeout=1500):
                    await item.click()
                    await asyncio.sleep(0.5)
                    logger.info("Deep research enabled.")
                    return
            except Exception:
                continue
        logger.warning("Could not find Deep research menu item.")
