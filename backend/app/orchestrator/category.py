from enum import Enum
import re
from typing import Optional


class ProductCategory(str, Enum):
    """Supported product investigation categories."""

    SMARTPHONE = "smartphone"
    LAPTOP = "laptop"
    HEADPHONES = "headphones"
    MONITOR = "monitor"
    TABLET = "tablet"
    CAMERA = "camera"


CATEGORY_ALIAS_MAP = {
    "smartphones": ProductCategory.SMARTPHONE.value,
    "smartphone": ProductCategory.SMARTPHONE.value,
    "phone": ProductCategory.SMARTPHONE.value,
    "mobile": ProductCategory.SMARTPHONE.value,
    "laptops": ProductCategory.LAPTOP.value,
    "laptop": ProductCategory.LAPTOP.value,
    "notebook": ProductCategory.LAPTOP.value,
    "headphones": ProductCategory.HEADPHONES.value,
    "audio": ProductCategory.HEADPHONES.value,
    "earbuds": ProductCategory.HEADPHONES.value,
    "monitors": ProductCategory.MONITOR.value,
    "monitor": ProductCategory.MONITOR.value,
    "tablets": ProductCategory.TABLET.value,
    "tablet": ProductCategory.TABLET.value,
    "cameras": ProductCategory.CAMERA.value,
    "camera": ProductCategory.CAMERA.value,
}


def normalize_category(category: Optional[str]) -> Optional[str]:
    """Normalize an explicit user-supplied category without ever defaulting to laptop."""
    if not category:
        return None
    cleaned = category.strip().lower()
    if not cleaned or cleaned in ("auto", "none", "unspecified"):
        return None
    return CATEGORY_ALIAS_MAP.get(cleaned, cleaned)


def classify_query_category(query: str) -> Optional[str]:
    """Deterministically infer product category from query tokens.

    Returns None when the query is ambiguous rather than guessing 'laptop'.
    """
    q = (query or "").strip().lower()
    if not q:
        return None

    # Check tablets before smartphones/laptops (e.g. 'Galaxy Tab' vs 'Galaxy S25', 'OnePlus Pad' vs 'OnePlus 13')
    if any(k in q for k in ("ipad", "galaxy tab", "oneplus pad", "tablet")):
        return ProductCategory.TABLET.value

    # Check headphones/audio before generic brand matches
    if any(k in q for k in ("wh-1000xm", "wf-1000xm", "airpods", "headphone", "earbud", "earphone", "tws", "neckband")):
        return ProductCategory.HEADPHONES.value

    # Check monitors before laptops
    if any(k in q for k in ("monitor", "ultrawide")):
        return ProductCategory.MONITOR.value

    # Check cameras
    if any(k in q for k in ("dslr", "mirrorless", "camera")):
        return ProductCategory.CAMERA.value

    # Check smartphones (explicit phone lines and brands)
    smartphone_patterns = [
        r"\biphone\b",
        r"\boneplus\s*(1[0-9]|nord|\d+[rst]?)\b",
        r"\bgalaxy\s*[szam]\d*\b",
        r"\bpixel\s*\d+\b",
        r"\bredmi\b",
        r"\bpoco\b",
        r"\brealme\b",
        r"\biqoo\b",
        r"\bsmartphone\b",
        r"\bmobile\s*phone\b",
    ]
    if any(re.search(pat, q) for pat in smartphone_patterns):
        return ProductCategory.SMARTPHONE.value

    # Check laptops
    laptop_patterns = [
        r"\bmacbook\b",
        r"\bxps\b",
        r"\bthinkpad\b",
        r"\bideapad\b",
        r"\bvivobook\b",
        r"\bzenbook\b",
        r"\binspiron\b",
        r"\bpavilion\b",
        r"\bchromebook\b",
        r"\bultrabook\b",
        r"\blaptop\b",
        r"\bnotebook\b",
    ]
    if any(re.search(pat, q) for pat in laptop_patterns):
        return ProductCategory.LAPTOP.value

    # Ambiguous query: return None rather than guessing
    return None
