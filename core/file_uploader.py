"""
File and image attachment handler for ChatGPT.
Handles local file paths, base64 vision images, and upload completion detection.
"""

import os
import re
import base64
import asyncio
import logging
from typing import List
from playwright.async_api import Page
from config.settings import settings
from config import selectors

logger = logging.getLogger("file_uploader")

class FileUploader:
    def __init__(self, temp_dir: str = settings.TEMP_UPLOADS_DIR):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)

    def prepare_file(self, file_source: str) -> str:
        """
        Validates local path or decodes base64 data URL to a local temporary file.
        """
        # Case 1: Local file path
        if os.path.exists(file_source):
            return os.path.abspath(file_source)

        # Case 2: Data URL (e.g. data:image/png;base64,iVBORw0KGgo...)
        if file_source.startswith("data:") and ";base64," in file_source:
            header, data = file_source.split(";base64,", 1)
            # Extract mime extension (e.g. image/png -> png)
            match = re.search(r"data:([^;]+)", header)
            mime = match.group(1) if match else "image/png"
            ext = mime.split("/")[-1] if "/" in mime else "png"
            if ext == "jpeg":
                ext = "jpg"

            temp_filename = f"upload_{os.urandom(6).hex()}.{ext}"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            with open(temp_path, "wb") as f:
                f.write(base64.b64decode(data))
            logger.info(f"Saved base64 image to temporary file: {temp_path}")
            return temp_path

        raise FileNotFoundError(f"File not found or invalid format: {file_source}")

    async def attach_files(self, page: Page, files: List[str]):
        """
        Attaches files to the ChatGPT prompt box using the hidden file input
        and waits for upload progress to complete.
        """
        if not files:
            return

        resolved_paths = [self.prepare_file(f) for f in files]
        logger.info(f"Attaching {len(resolved_paths)} file(s) to prompt...")

        file_input = page.locator(selectors.FILE_INPUT).first
        await file_input.set_input_files(resolved_paths)
        await asyncio.sleep(1.0)

        # Wait for file upload loading indicators to disappear
        logger.info("Waiting for file uploads to complete...")
        for _ in range(60):  # Wait up to 30s
            is_loading = False
            for sel in selectors.FILE_LOADING_INDICATOR:
                try:
                    if await page.locator(sel).first.is_visible(timeout=300):
                        is_loading = True
                        break
                except Exception:
                    pass
            if not is_loading:
                break
            await asyncio.sleep(0.5)

        logger.info("File upload attachment complete.")
