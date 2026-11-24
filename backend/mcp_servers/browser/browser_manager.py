import asyncio
import logging
from typing import Optional, Tuple
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from mcp_servers.browser.config import BrowserConfig

logger = logging.getLogger("webtruth.browser_manager")


class FetchedPageData:
    """Container for data retrieved from a Playwright navigation."""

    def __init__(
        self,
        source_url: str,
        final_url: str,
        title: str,
        status_code: Optional[int],
        html_content: str,
        error: Optional[str] = None,
    ):
        self.source_url = source_url
        self.final_url = final_url
        self.title = title
        self.status_code = status_code
        self.html_content = html_content
        self.error = error


class PlaywrightBrowserManager:
    """Manages headless Playwright browser instance and safe page loading."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        current_loop = asyncio.get_running_loop()
        if self._lock is None or self._loop != current_loop:
            self._lock = asyncio.Lock()
        return self._lock

    async def _ensure_browser(self) -> BrowserContext:
        """Initialize Playwright and BrowserContext if not running on the current loop."""
        current_loop = asyncio.get_running_loop()
        lock = self._get_lock()

        async with lock:
            if (
                self._context is not None
                and self._browser is not None
                and self._browser.is_connected()
                and self._loop == current_loop
            ):
                return self._context

            # If loop changed or browser disconnected, reset references
            if self._loop != current_loop or self._browser is None or not self._browser.is_connected():
                self._context = None
                self._browser = None
                self._playwright = None

            logger.info("Launching headless Chromium browser for WebTruth investigations...")
            self._loop = current_loop
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=BrowserConfig.HEADLESS,
                args=[
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._context = await self._browser.new_context(
                user_agent=BrowserConfig.USER_AGENT,
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
            )
            return self._context

    async def fetch_page(self, url: str, timeout_ms: Optional[int] = None) -> FetchedPageData:
        """Open a permitted URL and return HTML content and metadata with bounded timeouts."""
        is_allowed, reason = BrowserConfig.is_url_permitted(url)
        if not is_allowed:
            logger.warning("Blocked access to disallowed URL '%s': %s", url, reason)
            return FetchedPageData(
                source_url=url,
                final_url=url,
                title="",
                status_code=403,
                html_content="",
                error=reason,
            )

        effective_timeout_ms = timeout_ms if timeout_ms is not None else BrowserConfig.PAGE_TIMEOUT_MS
        hard_timeout_s = (effective_timeout_ms / 1000.0) + 2.5

        context = await self._ensure_browser()
        page: Optional[Page] = None
        try:
            async with asyncio.timeout(hard_timeout_s):
                page = await context.new_page()
                page.set_default_timeout(effective_timeout_ms)

                logger.info("Navigating to %s (timeout=%dms)", url, effective_timeout_ms)
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=effective_timeout_ms,
                )

                # Brief wait for dynamic DOM elements without waiting indefinitely for networkidle
                try:
                    await page.wait_for_timeout(350)
                except Exception:
                    pass

                title = await page.title()
                final_url = page.url
                status_code = response.status if response is not None else 200
                html_content = await page.content()

                logger.info(
                    "Successfully fetched '%s' (status=%s, title='%s', length=%d bytes)",
                    final_url,
                    status_code,
                    title,
                    len(html_content),
                )
                return FetchedPageData(
                    source_url=url,
                    final_url=final_url,
                    title=title,
                    status_code=status_code,
                    html_content=html_content,
                    error=None,
                )
        except TimeoutError:
            logger.warning("Browser navigation timed out for '%s' after %dms", url, effective_timeout_ms)
            return FetchedPageData(
                source_url=url,
                final_url=url,
                title="",
                status_code=504,
                html_content="",
                error=f"Browser navigation timed out after {effective_timeout_ms}ms",
            )
        except asyncio.CancelledError:
            logger.warning("Browser navigation cancelled for '%s'", url)
            raise
        except Exception as e:
            logger.error("Error during browser navigation to '%s': %s", url, str(e))
            return FetchedPageData(
                source_url=url,
                final_url=url,
                title="",
                status_code=500,
                html_content="",
                error=f"Browser navigation failed: {e}",
            )
        finally:
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass

    async def close(self) -> None:
        """Clean up and close browser instances."""
        lock = self._get_lock()
        async with lock:
            if self._context is not None:
                try:
                    await self._context.close()
                except Exception:
                    pass
                self._context = None
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            self._loop = None
            logger.info("Playwright browser closed and cleaned up")


# Global singleton instance
browser_manager = PlaywrightBrowserManager()
