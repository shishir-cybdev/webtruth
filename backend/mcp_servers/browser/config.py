import os
import re
from typing import Set
from urllib.parse import urlparse

# Default permitted public domains for product investigations
DEFAULT_ALLOWED_DOMAINS: Set[str] = {
    # Sample electronics & retail product sites
    "amazon.in",
    "www.amazon.in",
    "flipkart.com",
    "www.flipkart.com",
    "croma.com",
    "www.croma.com",
    "reliancedigital.in",
    "www.reliancedigital.in",
    "dell.com",
    "www.dell.com",
    "lenovo.com",
    "www.lenovo.com",
    "apple.com",
    "www.apple.com",
    "asus.com",
    "www.asus.com",
    "hp.com",
    "www.hp.com",
    "sony.co.in",
    "www.sony.co.in",
    # Local & testing domains
    "localhost",
    "127.0.0.1",
}

# Sensitive / private URL patterns that must be blocked
BLOCKED_PATH_PATTERNS = [
    r"/login",
    r"/signin",
    r"/sign-in",
    r"/account",
    r"/cart",
    r"/checkout",
    r"/order",
    r"/payment",
    r"/admin",
    r"/profile",
]


class BrowserConfig:
    """Configuration for Browser MCP server."""

    # Navigation and script timeouts (in milliseconds)
    PAGE_TIMEOUT_MS: int = int(os.getenv("BROWSER_PAGE_TIMEOUT_MS", "12000"))
    DISCOVERY_TIMEOUT_MS: int = int(os.getenv("BROWSER_DISCOVERY_TIMEOUT_MS", "8000"))
    DOM_WAIT_TIMEOUT_MS: int = int(os.getenv("BROWSER_DOM_WAIT_TIMEOUT_MS", "3000"))

    # Browser launch settings
    HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes")

    # Clean realistic user agent for public page inspection
    USER_AGENT: str = os.getenv(
        "BROWSER_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 WebTruth-Investigator/1.0",
    )

    @classmethod
    def get_allowed_domains(cls) -> Set[str]:
        """Return the effective set of permitted domains."""
        custom_domains = os.getenv("BROWSER_ALLOWED_DOMAINS", "")
        if custom_domains.strip():
            domains = {d.strip().lower() for d in custom_domains.split(",") if d.strip()}
            return domains | {"localhost", "127.0.0.1"}
        return set(DEFAULT_ALLOWED_DOMAINS)

    @classmethod
    def is_url_permitted(cls, url: str) -> tuple[bool, str]:
        """Check if a URL is permitted by policy.
        
        Returns:
            tuple: (is_permitted, reason)
        """
        if not url or not isinstance(url, str):
            return False, "URL is empty or invalid"

        cleaned_url = url.strip()

        # Allow local file:// URLs for test fixtures and offline verification
        if cleaned_url.startswith("file://"):
            return True, "Permitted local file fixture"

        try:
            parsed = urlparse(cleaned_url)
        except Exception as e:
            return False, f"Malformed URL: {e}"

        if parsed.scheme not in ("http", "https"):
            return False, f"Disallowed URL scheme: '{parsed.scheme}'. Only http, https, and file are permitted."

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False, "URL has no valid hostname"

        # Check domain allowlist
        allowed = cls.get_allowed_domains()
        # Direct match or subdomain match
        is_domain_allowed = any(
            hostname == d or hostname.endswith(f".{d}") for d in allowed
        )

        if not is_domain_allowed:
            return False, (
                f"Domain '{hostname}' is not in the permitted domain allowlist. "
                "Phase 2B restricts scraping to configured domains for safety and policy compliance."
            )

        # Block non-public authentication / checkout / private account paths
        path = parsed.path.lower()
        for pattern in BLOCKED_PATH_PATTERNS:
            if re.search(pattern, path):
                return False, f"URL path matches blocked pattern '{pattern}'. Only public product pages are permitted."

        return True, "URL is permitted"
