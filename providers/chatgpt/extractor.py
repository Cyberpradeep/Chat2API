"""
Response and metadata extractor for ChatGPT Web.
Captures generated markdown prose, collapsible thought processes, and web search citations.
"""

import asyncio
import logging
from typing import Dict, Any, List
from markdownify import markdownify as md
from playwright.async_api import Page
from config import selectors

logger = logging.getLogger("chatgpt_extractor")

async def get_assistant_turn_count(page: Page) -> int:
    """Counts how many assistant turns exist on the page."""
    for sel in selectors.ASSISTANT_TURNS:
        try:
            count = await page.locator(sel).count()
            if count > 0:
                return count
        except Exception:
            continue
    return 0


async def wait_for_completion(page: Page, previous_count: int, timeout_seconds: int = 180) -> Dict[str, Any]:
    """
    Watches generation lifecycle:
    1. Detects start via stop button appearance or count increment.
    2. Waits for stop button detachment and text stabilization.
    """
    start_time = asyncio.get_event_loop().time()

    # Phase 1: Wait for generation to begin
    generation_started = False
    while (asyncio.get_event_loop().time() - start_time) < 20:
        for stop_sel in selectors.STOP_BUTTON:
            try:
                if await page.locator(stop_sel).first.is_visible(timeout=200):
                    generation_started = True
                    break
            except Exception:
                pass
        if generation_started:
            break

        count = await get_assistant_turn_count(page)
        if count > previous_count:
            generation_started = True
            break

        await asyncio.sleep(0.3)

    logger.info(f"Generation activity detected: {generation_started}")

    # Phase 2: Wait for generation completion and text stabilization
    last_text = ""
    stable_count = 0

    while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
        # Check if stop button is present
        is_generating = False
        for stop_sel in selectors.STOP_BUTTON:
            try:
                if await page.locator(stop_sel).first.is_visible(timeout=200):
                    is_generating = True
                    break
            except Exception:
                pass

        current_data = await extract_latest_response(page)
        current_text = current_data["content"]

        if not is_generating and len(current_text) > 0:
            if current_text == last_text:
                stable_count += 1
                if stable_count >= 3:  # Unchanged for ~1.5s after stop button detached
                    logger.info("Generation confirmed complete.")
                    return current_data
            else:
                stable_count = 0

        last_text = current_text
        await asyncio.sleep(0.5)

    if last_text:
        logger.warning("Generation timed out, returning last captured content.")
        return await extract_latest_response(page)

    raise TimeoutError(f"No response received from ChatGPT within {timeout_seconds} seconds.")


async def extract_latest_response(page: Page) -> Dict[str, Any]:
    """
    Extracts the latest assistant answer, plus any thought process or citations.
    """
    content = ""
    thought_process = None
    sources: List[str] = []

    for sel in selectors.ASSISTANT_TURNS:
        try:
            turns = page.locator(sel)
            count = await turns.count()
            if count == 0:
                continue

            last_turn = turns.nth(count - 1)

            # 1. Extract thought process (Think mode) if present
            for thought_sel in selectors.THOUGHT_CONTAINERS:
                try:
                    thought_elem = last_turn.locator(thought_sel).first
                    if await thought_elem.is_visible(timeout=200):
                        thought_process = (await thought_elem.inner_text()).strip()
                        break
                except Exception:
                    pass

            # 2. Extract sources / citations if present
            for src_sel in selectors.SOURCE_CONTAINERS:
                try:
                    src_elems = last_turn.locator(src_sel)
                    src_count = await src_elems.count()
                    for i in range(src_count):
                        href = await src_elems.nth(i).get_attribute("href")
                        text = await src_elems.nth(i).inner_text()
                        if href:
                            sources.append(f"[{text.strip()}]({href})")
                        elif text:
                            sources.append(text.strip())
                except Exception:
                    pass

            # 3. Extract main content (Markdown prose)
            prose_elem = last_turn.locator(".markdown, .prose, div.prose").first
            if await prose_elem.is_visible(timeout=300):
                html = await prose_elem.inner_html()
                content = md(html, strip=["button"]).strip()
            else:
                content = (await last_turn.inner_text()).strip()

            if content:
                break
        except Exception:
            continue

    return {
        "content": content,
        "thought_process": thought_process,
        "sources": sources
    }
