import re
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProductMatchStatus(str, Enum):
    """Classification of how well an extracted page matches the target investigation query."""

    EXACT_MATCH = "EXACT_MATCH"
    RELATED_VARIANT = "RELATED_VARIANT"
    ACCESSORY = "ACCESSORY"
    BRAND_MISMATCH = "BRAND_MISMATCH"
    MODEL_MISMATCH = "MODEL_MISMATCH"
    CATEGORY_MISMATCH = "CATEGORY_MISMATCH"
    INSUFFICIENT_IDENTITY = "INSUFFICIENT_IDENTITY"


class ProductIdentityMatchResult(BaseModel):
    """Deterministic identity comparison outcome between query and extracted page."""

    match_status: ProductMatchStatus
    query_brand: Optional[str] = None
    query_model_tokens: List[str] = Field(default_factory=list)
    extracted_brand: Optional[str] = None
    extracted_model: Optional[str] = None
    extracted_category: Optional[str] = None
    reason: str


KNOWN_BRANDS = {
    "oneplus",
    "apple",
    "samsung",
    "dell",
    "lenovo",
    "hp",
    "asus",
    "acer",
    "sony",
    "xiaomi",
    "redmi",
    "poco",
    "realme",
    "vivo",
    "iqoo",
    "oppo",
    "motorola",
    "moto",
    "google",
    "pixel",
    "nothing",
    "lava",
    "nokia",
    "micromax",
    "msi",
    "lg",
    "boat",
    "jbl",
    "bose",
    "sennheiser",
    "honor",
    "huawei",
    "tecno",
    "infinix",
}

ACCESSORY_KEYWORDS = {
    "case",
    "cover",
    "back cover",
    "flip cover",
    "bumper",
    "tempered glass",
    "screen guard",
    "screen protector",
    "charger",
    "adapter",
    "cable",
    "usb cable",
    "power bank",
    "powerbank",
    "skin",
    "wrap",
    "holder",
    "stand",
    "mount",
    "stylus",
    "sleeve",
    "backpack",
    "segments",
    "strap",
    "band",
    "lens protector",
    "camera ring",
    "earbuds",
    "tws",
    "neckband",
    "dock",
    "dongle",
}

# Variant suffixes that define a distinct model SKU/edition (e.g. 13 vs 13S, 13R, 13 Pro, 15 Plus)
VARIANT_SUFFIX_WORDS = {
    "pro",
    "max",
    "plus",
    "ultra",
    "lite",
    "mini",
    "se",
    "fe",
    "neo",
    "air",
    "studio",
    "t",
    "s",
    "r",
    "x",
    "c",
    "ce",
    "nord",
    "fold",
    "flip",
    "edge",
    "turbo",
    "gt",
}

CATEGORY_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "laptop": ("laptop", "notebook", "macbook", "thinkpad", "xps", "ultrabook", "chromebook", "vivobook", "zenbook", "inspiron", "pavilion", "ideapad"),
    "smartphone": ("smartphone", "mobile phone", "5g phone", "android phone", "iphone", "galaxy s", "oneplus 13", "oneplus 12", "redmi", "poco"),
    "tablet": ("tablet", "ipad", "galaxy tab", "oneplus pad"),
    "headphones": ("headphones", "earbuds", "earphones", "tws", "neckband", "wh-1000xm", "airpods"),
    "monitor": ("monitor", "gaming monitor", "4k display", "ultrawide"),
    "camera": ("mirrorless camera", "dslr", "action camera", "eos", "alpha"),
}


def tokenize_alnum(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric whole tokens."""
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def detect_brand_in_text(text: str, explicit_brand: Optional[str] = None) -> Optional[str]:
    """Extract canonical lowercase brand from explicit field or text tokens."""
    if explicit_brand:
        eb_tokens = tokenize_alnum(explicit_brand)
        for t in eb_tokens:
            if t in KNOWN_BRANDS:
                return "google" if t == "pixel" else ("motorola" if t == "moto" else t)
        if eb_tokens:
            return eb_tokens[0]

    tokens = tokenize_alnum(text)
    for t in tokens:
        if t in KNOWN_BRANDS:
            return "google" if t == "pixel" else ("motorola" if t == "moto" else t)
    return None


def infer_category(
    product_name: Optional[str],
    page_title: Optional[str] = None,
    specs: Optional[Dict[str, str]] = None,
    url: Optional[str] = None,
) -> Optional[str]:
    """Infer product category deterministically from actual page content."""
    combined = " ".join([
        product_name or "",
        page_title or "",
        " ".join(f"{k} {v}" for k, v in (specs or {}).items()),
    ]).lower()

    # Check explicit category keywords in order of specificity
    for cat, markers in CATEGORY_KEYWORDS.items():
        if any(m in combined for m in markers):
            return cat

    # Fallback spec-based signals
    if specs:
        keys_lower = {k.lower() for k in specs.keys()}
        if any(k in keys_lower for k in ("ram", "processor", "cpu", "gpu", "ssd")):
            if "mobile" in combined or "sim" in combined or "mah" in combined:
                return "smartphone"
            return "laptop"

    return None


def extract_model_tokens(text: str, brand: Optional[str] = None) -> List[str]:
    """Extract ordered model-identifying tokens from query or product title.
    
    Ignores generic retail noise (5G, 12GB, 256GB, colors, 'smartphone', 'laptop', etc.).
    Preserves exact alphanumeric model tokens like '13', '13s', '13r', '9530', 'pro'.
    """
    noise_words = {
        "the", "and", "with", "for", "new", "official", "store", "india", "online",
        "buy", "price", "specs", "5g", "4g", "lte", "wifi", "ram", "rom", "ssd", "hdd",
        "storage", "memory", "smartphone", "mobile", "phone", "laptop", "notebook",
        "tablet", "monitor", "camera", "headphones", "black", "white", "blue", "green",
        "silver", "gold", "grey", "gray", "arctic", "dawn", "midnight", "obsidian",
        "emerald", "edition", "smarter", "ai", "lifetime", "display", "warranty",
        "unlocked", "dual", "sim", "gb", "tb", "mah", "inch", "inches", "cm",
    }
    tokens = tokenize_alnum(text)
    model_tokens: List[str] = []
    for t in tokens:
        if brand and t == brand.lower():
            continue
        if t in KNOWN_BRANDS:
            continue
        if t in noise_words:
            continue
        # Filter storage/RAM sizes like 12gb, 256gb, 1tb, 512gb, 16gb
        if re.fullmatch(r"\d+(gb|tb|mb|mah|hz|w|whr)", t):
            continue
        model_tokens.append(t)
    return model_tokens


def _is_accessory_text(text: str, query: str) -> bool:
    """Return True if candidate text describes an accessory while query does not."""
    text_lower = (text or "").lower()
    query_lower = (query or "").lower()
    for kw in ACCESSORY_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", text_lower) and not re.search(rf"\b{re.escape(kw)}\b", query_lower):
            return True
    return False


def evaluate_product_identity(
    query: str,
    extracted_product_name: Optional[str],
    extracted_brand: Optional[str] = None,
    extracted_model: Optional[str] = None,
    page_title: Optional[str] = None,
    specs: Optional[Dict[str, str]] = None,
    source_url: Optional[str] = None,
    expected_category: Optional[str] = None,
) -> ProductIdentityMatchResult:
    """Strictly classify whether an extracted page matches the target investigation product."""
    q_brand = detect_brand_in_text(query)
    q_tokens = extract_model_tokens(query, q_brand)

    cand_text = " ".join(p for p in [extracted_product_name, page_title, extracted_model] if p).strip()
    if not cand_text:
        return ProductIdentityMatchResult(
            match_status=ProductMatchStatus.INSUFFICIENT_IDENTITY,
            query_brand=q_brand,
            query_model_tokens=q_tokens,
            reason="Page lacks product name, title, or model identity.",
        )

    c_brand = detect_brand_in_text(cand_text, explicit_brand=extracted_brand)
    c_category = infer_category(extracted_product_name, page_title, specs, source_url)

    # 1. Accessory check (even if brand matches, e.g. 'OnePlus Snapdragon Segments' or 'OnePlus 13 Back Cover')
    if _is_accessory_text(extracted_product_name or page_title or "", query):
        return ProductIdentityMatchResult(
            match_status=ProductMatchStatus.ACCESSORY,
            query_brand=q_brand,
            query_model_tokens=q_tokens,
            extracted_brand=c_brand,
            extracted_model=extracted_model,
            extracted_category=c_category,
            reason=f"Detected accessory or peripheral rather than primary product ('{extracted_product_name or page_title}').",
        )

    # 2. Category check
    if expected_category and c_category:
        exp_cat = expected_category.strip().lower()
        if exp_cat != c_category:
            return ProductIdentityMatchResult(
                match_status=ProductMatchStatus.CATEGORY_MISMATCH,
                query_brand=q_brand,
                query_model_tokens=q_tokens,
                extracted_brand=c_brand,
                extracted_model=extracted_model,
                extracted_category=c_category,
                reason=f"Category mismatch: expected '{exp_cat}', page describes '{c_category}'.",
            )

    # 3. Brand compatibility check
    if q_brand:
        if not c_brand:
            return ProductIdentityMatchResult(
                match_status=ProductMatchStatus.INSUFFICIENT_IDENTITY,
                query_brand=q_brand,
                query_model_tokens=q_tokens,
                extracted_brand=None,
                extracted_model=extracted_model,
                extracted_category=c_category,
                reason=f"Could not verify brand '{q_brand}' on product page.",
            )
        if c_brand != q_brand:
            return ProductIdentityMatchResult(
                match_status=ProductMatchStatus.BRAND_MISMATCH,
                query_brand=q_brand,
                query_model_tokens=q_tokens,
                extracted_brand=c_brand,
                extracted_model=extracted_model,
                extracted_category=c_category,
                reason=f"Brand mismatch: expected '{q_brand}', found '{c_brand}'.",
            )

    # 4. Token-aware model matching (no loose substring matching!)
    if not q_tokens:
        # Query had only brand or generic term; cannot confirm exact model
        return ProductIdentityMatchResult(
            match_status=ProductMatchStatus.INSUFFICIENT_IDENTITY,
            query_brand=q_brand,
            query_model_tokens=q_tokens,
            extracted_brand=c_brand,
            extracted_model=extracted_model,
            extracted_category=c_category,
            reason="Query does not specify an identifiable model number/name.",
        )

    # Use primary product name / H1 / model for model token extraction (preferring product_name over verbose SEO title)
    primary_cand_text = " ".join(p for p in [extracted_product_name, extracted_model] if p).strip() or (page_title or "")
    c_tokens = extract_model_tokens(primary_cand_text, c_brand)
    if not c_tokens:
        return ProductIdentityMatchResult(
            match_status=ProductMatchStatus.INSUFFICIENT_IDENTITY,
            query_brand=q_brand,
            query_model_tokens=q_tokens,
            extracted_brand=c_brand,
            extracted_model=extracted_model,
            extracted_category=c_category,
            reason="Extracted page lacks identifiable model tokens.",
        )

    # Check if every query model token appears as an EXACT whole token in candidate
    c_token_set = set(c_tokens)
    q_token_set = set(q_tokens)

    # Check for variant-suffixed tokens like '13s' or '13r' when query has '13'
    # Example: query=['13'], candidate=['13s'] -> RELATED_VARIANT
    for qt in q_tokens:
        if qt not in c_token_set:
            # Check if candidate has a variant token sharing the base alphanumeric prefix (e.g. '13s', '13r', '13t', '13a')
            variant_matches = [
                ct for ct in c_tokens
                if (ct.startswith(qt) and len(ct) > len(qt) and ct[len(qt):].isalpha())
                or (qt.startswith(ct) and len(qt) > len(ct) and qt[len(ct):].isalpha())
            ]
            if variant_matches:
                return ProductIdentityMatchResult(
                    match_status=ProductMatchStatus.RELATED_VARIANT,
                    query_brand=q_brand,
                    query_model_tokens=q_tokens,
                    extracted_brand=c_brand,
                    extracted_model=extracted_model or extracted_product_name,
                    extracted_category=c_category,
                    reason=f"Related model variant detected: query expects '{qt}', page specifies '{variant_matches[0]}'.",
                )
            return ProductIdentityMatchResult(
                match_status=ProductMatchStatus.MODEL_MISMATCH,
                query_brand=q_brand,
                query_model_tokens=q_tokens,
                extracted_brand=c_brand,
                extracted_model=extracted_model or extracted_product_name,
                extracted_category=c_category,
                reason=f"Model mismatch: required model token '{qt}' not found in '{primary_cand_text}'.",
            )

    # All query model tokens matched as exact whole tokens!
    # Now check if candidate introduces an extra variant suffix (e.g. query='OnePlus 13', candidate='OnePlus 13 Pro' or 'OnePlus 13 S')
    extra_tokens = c_token_set - q_token_set
    extra_variants = [t for t in extra_tokens if t in VARIANT_SUFFIX_WORDS]
    if extra_variants:
        return ProductIdentityMatchResult(
            match_status=ProductMatchStatus.RELATED_VARIANT,
            query_brand=q_brand,
            query_model_tokens=q_tokens,
            extracted_brand=c_brand,
            extracted_model=extracted_model or extracted_product_name,
            extracted_category=c_category,
            reason=f"Related variant detected: page includes variant qualifier(s) {extra_variants} not in query.",
        )

    return ProductIdentityMatchResult(
        match_status=ProductMatchStatus.EXACT_MATCH,
        query_brand=q_brand,
        query_model_tokens=q_tokens,
        extracted_brand=c_brand,
        extracted_model=extracted_model or extracted_product_name,
        extracted_category=c_category,
        reason=f"Exact brand ('{c_brand or 'any'}') and model ({q_tokens}) match confirmed.",
    )
