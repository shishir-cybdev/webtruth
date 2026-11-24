import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

from mcp_servers.browser.schemas import (
    ExtractedProductDataResult,
    PageEvidenceRecordResult,
    PageMetadataResult,
    PriceFact,
    StructuredProductDataResult,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.extractor")


def clean_text(text: Optional[str]) -> Optional[str]:
    """Strip extraneous whitespace and return None if empty."""
    if text is None:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def parse_numeric_price(price_str: Optional[str]) -> Optional[float]:
    """Extract a numeric float from price text without mutating currency or assuming units."""
    if not price_str:
        return None
    # Remove currency symbols and comma separators
    cleaned = re.sub(r"[^\d.]", "", price_str)
    # Check if we have multiple dots or a clean float
    try:
        if cleaned:
            return float(cleaned)
    except Exception:
        pass
    return None


def detect_currency(price_str: Optional[str]) -> Optional[str]:
    """Detect currency symbol or code from displayed price text."""
    if not price_str:
        return None
    if "₹" in price_str or "INR" in price_str or "Rs" in price_str or "rs" in price_str:
        return "INR"
    if "$" in price_str or "USD" in price_str:
        return "USD"
    if "€" in price_str or "EUR" in price_str:
        return "EUR"
    if "£" in price_str or "GBP" in price_str:
        return "GBP"
    return None


BOILERPLATE_HEADING_MARKERS = (
    "add to your order",
    "added to cart",
    "shopping cart",
    "frequently bought together",
    "sign in",
    "customer reviews",
    "sponsored",
    "related products",
    "compare with similar items",
)

DISQUALIFIED_PRICE_CONTEXT_MARKERS = (
    "protection",
    "applecare",
    "extended warranty",
    "warranty plan",
    "add to your order",
    "added to cart",
    "frequently bought",
    "accessory",
    "bundle",
    "upsell",
    "a-text-price",
    "basisprice",
    "strike",
    "list-price",
    "mrp",
    "emi",
    "installment",
    "per month",
    "/mo",
)


def _is_boilerplate_heading(text: Optional[str]) -> bool:
    """Return True if a heading is a UI/cart/modal label rather than a product title."""
    if not text:
        return True
    lowered = text.strip().lower()
    if len(lowered) < 3:
        return True
    return any(marker in lowered for marker in BOILERPLATE_HEADING_MARKERS)


def _is_disqualified_price_context(el: Any, price_text: str) -> bool:
    """Return True if a price element belongs to upsells, protection plans, EMIs, or crossed-out MRP."""
    if not price_text:
        return True
    lowered_text = price_text.lower()
    if any(m in lowered_text for m in ("/mo", "per month", "emi", "installment", "save", "off")):
        return True

    # Inspect the element and up to 4 ancestor containers for disqualifying attributes;
    # only check text content on the element itself and its immediate parent to avoid sibling-box false positives.
    curr = el
    for depth in range(5):
        if curr is None:
            break
        if getattr(curr, "attrs", None):
            if curr.attrs.get("data-a-strike") == "true":
                return True
            el_id = str(curr.attrs.get("id") or "").lower()
            el_classes = " ".join(curr.attrs.get("class") or []).lower()
            combined_attr = f"{el_id} {el_classes}"
            if any(m in combined_attr for m in ("a-text-price", "basisprice", "strike", "protection", "warranty", "upsell", "bundle", "accessory", "cart-modal", "attach", "emi")):
                return True
        if depth <= 1:
            curr_text = (clean_text(curr.get_text(" ", strip=True)) or "").lower()
            if len(curr_text) < 250 and any(m in curr_text for m in ("add to your order", "protection plan", "applecare", "extended warranty", "no cost emi", "per month")):
                return True
        curr = getattr(curr, "parent", None)

    return False


class ProductExtractor:
    """Extracts structured, semi-structured, and verifiable evidence from HTML."""

    @classmethod
    def parse_json_ld(cls, soup: BeautifulSoup) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Extract all JSON-LD objects and collect detected schema.org types."""
        json_ld_products: List[Dict[str, Any]] = []
        detected_types: List[str] = []

        script_tags = soup.find_all("script", type="application/ld+json")
        for script in script_tags:
            content = script.string or script.get_text()
            if not content:
                continue
            try:
                data = json.loads(content.strip())
            except Exception as e:
                logger.debug("Failed to parse JSON-LD block: %s", e)
                continue

            # Flatten @graph or list of items
            items_to_check = []
            if isinstance(data, list):
                items_to_check.extend(data)
            elif isinstance(data, dict):
                if "@graph" in data and isinstance(data["@graph"], list):
                    items_to_check.extend(data["@graph"])
                else:
                    items_to_check.append(data)

            for item in items_to_check:
                if not isinstance(item, dict):
                    continue
                schema_type = item.get("@type")
                if schema_type:
                    if isinstance(schema_type, list):
                        detected_types.extend(schema_type)
                    else:
                        detected_types.append(schema_type)

                # Check for Product schema
                is_product = False
                if isinstance(schema_type, str) and schema_type.lower() == "product":
                    is_product = True
                elif isinstance(schema_type, list) and any(
                    isinstance(t, str) and t.lower() == "product" for t in schema_type
                ):
                    is_product = True

                if is_product:
                    json_ld_products.append(item)

        # Unique types while preserving order
        unique_types = list(dict.fromkeys(detected_types))
        return json_ld_products, unique_types

    @classmethod
    def parse_metadata(cls, soup: BeautifulSoup) -> Tuple[Dict[str, str], Dict[str, str], Optional[str]]:
        """Extract OpenGraph tags, general meta tags, and canonical URL."""
        open_graph: Dict[str, str] = {}
        meta_tags: Dict[str, str] = {}
        canonical_url: Optional[str] = None

        # Canonical link
        canonical_tag = soup.find("link", rel="canonical")
        if canonical_tag and canonical_tag.get("href"):
            canonical_url = str(canonical_tag.get("href")).strip()

        # Meta tags
        for meta in soup.find_all("meta"):
            prop = meta.get("property") or meta.get("name")
            val = meta.get("content")
            if not prop or val is None:
                continue
            prop_str = str(prop).strip()
            val_str = str(val).strip()

            if prop_str.startswith("og:"):
                open_graph[prop_str] = val_str
            else:
                meta_tags[prop_str] = val_str

        return open_graph, meta_tags, canonical_url

    @classmethod
    def parse_specifications_table(cls, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract key-value specifications from HTML tables and definition lists."""
        specs: Dict[str, str] = {}

        # Look in tables
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    k = clean_text(th.get_text())
                    v = clean_text(td.get_text())
                    if k and v and len(k) < 60 and len(v) < 300:
                        specs[k] = v
                else:
                    cells = row.find_all("td")
                    if len(cells) == 2:
                        k = clean_text(cells[0].get_text())
                        v = clean_text(cells[1].get_text())
                        if k and v and len(k) < 60 and len(v) < 300:
                            specs[k] = v

        # Look in definition lists <dl>
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                k = clean_text(dt.get_text())
                v = clean_text(dd.get_text())
                if k and v and len(k) < 60 and len(v) < 300:
                    specs[k] = v

        return specs

    @classmethod
    def extract_structured_data(
        cls, html_content: str, source_url: str
    ) -> StructuredProductDataResult:
        """Extract all JSON-LD and meta/OpenGraph structured data."""
        timestamp = current_utc_iso()
        if not html_content:
            return StructuredProductDataResult(
                source_url=source_url,
                capture_timestamp_utc=timestamp,
                error="Empty HTML content",
            )

        soup = BeautifulSoup(html_content, "html.parser")
        json_ld_products, detected_types = cls.parse_json_ld(soup)
        open_graph, meta_tags, _ = cls.parse_metadata(soup)

        return StructuredProductDataResult(
            source_url=source_url,
            capture_timestamp_utc=timestamp,
            json_ld_products=json_ld_products,
            open_graph=open_graph,
            meta_data=meta_tags,
            detected_schemas=detected_types,
        )

    @classmethod
    def _extract_dom_product_title(cls, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title from DOM using specific product selectors before generic h1."""
        priority_selectors = (
            "#productTitle",
            "#title",
            "[data-testid='product-title']",
            "h1[id*='title']",
            "h1[class*='title']",
        )
        for sel in priority_selectors:
            el = soup.select_one(sel)
            if el:
                candidate = clean_text(el.get_text())
                if candidate and not _is_boilerplate_heading(candidate):
                    return candidate

        for h1 in soup.find_all("h1"):
            candidate = clean_text(h1.get_text())
            if candidate and not _is_boilerplate_heading(candidate):
                return candidate

        return None

    @classmethod
    def _extract_dom_product_price(cls, soup: BeautifulSoup) -> Optional[PriceFact]:
        """Extract main product price from DOM while rejecting upsells, EMIs, and crossed-out prices."""
        priority_selectors = (
            "#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price) .a-offscreen",
            "#corePrice_feature_div .a-price:not(.a-text-price) .a-offscreen",
            "#apex_desktop .a-price:not(.a-text-price) .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
        )
        for sel in priority_selectors:
            for el in soup.select(sel):
                price_text = clean_text(el.get_text())
                if not price_text or _is_disqualified_price_context(el, price_text):
                    continue
                num_p = parse_numeric_price(price_text)
                if num_p is not None and num_p > 0:
                    return PriceFact(
                        displayed_text=price_text,
                        numeric_amount=num_p,
                        currency=detect_currency(price_text),
                        is_inferred=False,
                    )

        fallback_candidates = (
            soup.find_all(attrs={"data-price": True})
            + soup.find_all(class_=re.compile(r"price|product-price|offer-price", re.I))
            + soup.find_all(id=re.compile(r"price|product-price", re.I))
        )
        for el in fallback_candidates:
            price_text = clean_text(el.get_text())
            if not price_text or _is_disqualified_price_context(el, price_text):
                continue
            num_p = parse_numeric_price(price_text)
            curr = detect_currency(price_text)
            if num_p is not None and num_p > 0 and curr is not None:
                return PriceFact(
                    displayed_text=price_text,
                    numeric_amount=num_p,
                    currency=curr,
                    is_inferred=True,
                )

        return None

    @classmethod
    def extract_product_data(
        cls, html_content: str, source_url: str
    ) -> ExtractedProductDataResult:
        """Extract authoritative product details combining JSON-LD, OpenGraph, and DOM."""
        timestamp = current_utc_iso()
        if not html_content:
            return ExtractedProductDataResult(
                source_url=source_url,
                capture_timestamp_utc=timestamp,
                error="Empty HTML content",
            )

        soup = BeautifulSoup(html_content, "html.parser")
        json_ld_products, _ = cls.parse_json_ld(soup)
        open_graph, meta_tags, _ = cls.parse_metadata(soup)
        specs = cls.parse_specifications_table(soup)

        product_name: Optional[str] = None
        brand: Optional[str] = None
        model: Optional[str] = None
        price_fact: Optional[PriceFact] = None
        availability: Optional[str] = None
        warranty: Optional[str] = None
        return_policy: Optional[str] = None
        method = "dom"

        # 1. First priority: JSON-LD Product Schema
        if json_ld_products:
            prod = json_ld_products[0]
            method = "json_ld"
            ld_name = clean_text(prod.get("name"))
            if not _is_boilerplate_heading(ld_name):
                product_name = ld_name
            if isinstance(prod.get("brand"), dict):
                brand = clean_text(prod["brand"].get("name"))
            elif isinstance(prod.get("brand"), str):
                brand = clean_text(prod["brand"])
            model = clean_text(prod.get("model") or prod.get("sku") or prod.get("mpn"))

            # Offers for price & availability
            offers = prod.get("offers")
            offer_obj = None
            if isinstance(offers, list) and offers:
                offer_obj = offers[0]
            elif isinstance(offers, dict):
                offer_obj = offers

            if offer_obj and isinstance(offer_obj, dict):
                raw_price = offer_obj.get("price")
                curr = offer_obj.get("priceCurrency")
                avail = offer_obj.get("availability")
                if raw_price is not None:
                    num_p = parse_numeric_price(str(raw_price))
                    if num_p is not None and num_p > 0:
                        displayed = f"{curr} {raw_price}" if curr else str(raw_price)
                        price_fact = PriceFact(
                            displayed_text=displayed,
                            numeric_amount=num_p,
                            currency=curr or detect_currency(str(raw_price)),
                            is_inferred=False,
                        )
                if avail:
                    availability = str(avail).split("/")[-1]

            if prod.get("warranty"):
                warranty = clean_text(str(prod.get("warranty")))

        # 2. Second priority / Fallback: OpenGraph tags
        if not product_name and open_graph.get("og:title"):
            og_name = clean_text(open_graph["og:title"])
            if not _is_boilerplate_heading(og_name):
                product_name = og_name
                if method == "dom":
                    method = "opengraph"

        if not price_fact and open_graph.get("og:price:amount"):
            raw_p = open_graph["og:price:amount"]
            num_p = parse_numeric_price(raw_p)
            if num_p is not None and num_p > 0:
                curr = open_graph.get("og:price:currency")
                displayed = f"{curr} {raw_p}" if curr else raw_p
                price_fact = PriceFact(
                    displayed_text=displayed,
                    numeric_amount=num_p,
                    currency=curr or detect_currency(raw_p),
                    is_inferred=False,
                )
                if method == "dom":
                    method = "opengraph"

        # 3. Third priority / Fallback: Explicit DOM Product Title Selectors (never blindly pick modal/cart h1)
        if not product_name:
            product_name = cls._extract_dom_product_title(soup)

        extraction_warnings: List[str] = []
        if not price_fact:
            price_fact = cls._extract_dom_product_price(soup)
            if not price_fact:
                extraction_warnings.append("Actual main product price could not be established; kept unavailable (null).")

        # Look for availability in DOM if still missing
        if not availability:
            avail_el = soup.find(
                class_=re.compile(r"availability|stock-status|in-stock", re.I)
            )
            if avail_el:
                availability = clean_text(avail_el.get_text())

        # Look for warranty in specs if found
        if not warranty:
            for k, v in specs.items():
                if "warranty" in k.lower():
                    warranty = v
                    break

        model_number = None
        if json_ld_products:
            p0 = json_ld_products[0]
            model_number = p0.get("mpn") or p0.get("sku")

        result = ExtractedProductDataResult(
            source_url=source_url,
            capture_timestamp_utc=timestamp,
            product_name=product_name,
            brand=brand,
            model=model,
            model_number=str(model_number) if model_number else None,
            price=price_fact,
            availability=availability,
            specifications=specs,
            warranty=warranty,
            return_policy=return_policy,
            extraction_method=method,
            extraction_warnings=extraction_warnings,
        )

        is_valid, val_err, block_reason = cls.validate_page_for_product_evidence(
            source_url=source_url,
            final_url=source_url,
            status_code=200,
            page_title=clean_text(soup.title.get_text() if soup.title else ""),
            html_content=html_content,
            extracted=result,
            has_json_ld_product=bool(json_ld_products),
        )
        result.is_valid_product_page = is_valid
        result.validation_error = val_err
        result.block_reason = block_reason
        if not is_valid:
            # Do not keep generic homepage/error titles as product_name
            if block_reason in ("not_found_page", "captcha_or_antibot", "generic_homepage", "http_error"):
                result.product_name = None
        return result

    @classmethod
    def validate_page_for_product_evidence(
        cls,
        source_url: str,
        final_url: Optional[str],
        status_code: Optional[int],
        page_title: Optional[str],
        html_content: str,
        extracted: Optional[ExtractedProductDataResult] = None,
        has_json_ld_product: bool = False,
        expected_category: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Validate whether a fetched page is a genuine, unblocked product page."""
        from urllib.parse import urlparse

        if status_code is not None and status_code >= 400:
            if status_code == 404:
                return False, "Page Not Found (HTTP 404)", "not_found_page"
            if status_code in (403, 429, 503):
                return False, f"Retailer blocked automated access (HTTP {status_code})", "captcha_or_antibot"
            return False, f"HTTP error status {status_code}", "http_error"

        title_lower = (page_title or "").lower()
        soup = BeautifulSoup(html_content or "", "html.parser")
        body_text = (clean_text(soup.get_text(" ")[:3500]) or "").lower()
        h1_el = soup.find("h1")
        h1_lower = (clean_text(h1_el.get_text()) or "").lower() if h1_el else ""

        captcha_markers = [
            "robot check",
            "enter the characters you see",
            "verify you are human",
            "just a moment...",
            "attention required! | cloudflare",
            "access denied",
            "automated access",
            "sorry, we just need to make sure you're not a robot",
        ]
        for marker in captcha_markers:
            if marker in title_lower or marker in body_text:
                return (
                    False,
                    "Retailer presented an anti-bot or CAPTCHA challenge (not bypassed per policy)",
                    "captcha_or_antibot",
                )

        not_found_markers = [
            "page not found",
            "404 not found",
            "404 error",
            "sorry! we couldn't find that page",
            "looking for something?",
            "we couldn't find the page",
            "this page isn't available",
        ]
        for marker in not_found_markers:
            if marker in title_lower or marker in h1_lower:
                return False, f"Page Not Found / Error page detected ('{page_title}')", "not_found_page"

        parsed = urlparse(final_url or source_url)
        is_root_path = parsed.scheme in ("http", "https") and parsed.path.strip("/") == ""
        has_product_signals = bool(
            has_json_ld_product
            or (extracted and (extracted.price or len(extracted.specifications) > 0))
        )

        generic_titles = [
            "online shopping site in india",
            "online shopping india",
            "dell official site",
            "computers, monitors & technology solutions",
        ]
        if (is_root_path or any(g in title_lower for g in generic_titles)) and not has_product_signals:
            return (
                False,
                f"Generic retailer homepage detected without product data ('{page_title}')",
                "generic_homepage",
            )

        if extracted and not extracted.product_name and not has_product_signals:
            return (
                False,
                "No product identity, price, or specifications found on page",
                "no_product_identity",
            )

        if expected_category and extracted:
            pname_lower = f"{extracted.product_name or ''} {page_title or ''} {h1_lower}".lower()
            cat_lower = expected_category.lower()
            if cat_lower in ("smartphone", "phone", "mobile") and any(
                w in pname_lower for w in ("laptop", "notebook", "desktop", "monitor")
            ):
                return (
                    False,
                    f"Product category mismatch: requested '{expected_category}', page describes '{extracted.product_name}'",
                    "category_mismatch",
                )
            if cat_lower == "laptop" and any(
                w in pname_lower for w in ("smartphone", "earbuds", "refrigerator", "washing machine")
            ):
                return (
                    False,
                    f"Product category mismatch: requested '{expected_category}', page describes '{extracted.product_name}'",
                    "category_mismatch",
                )

        return True, None, None

    @classmethod
    def generate_page_evidence(
        cls, html_content: str, source_url: str, page_title: Optional[str] = None
    ) -> PageEvidenceRecordResult:
        """Capture verifiable text snippets and generate SHA-256 evidence fingerprint."""
        timestamp = current_utc_iso()
        if not html_content:
            return PageEvidenceRecordResult(
                source_url=source_url,
                capture_timestamp_utc=timestamp,
                page_title=page_title,
                sha256_hash="",
                error="Empty HTML content",
            )

        soup = BeautifulSoup(html_content, "html.parser")
        _, meta_tags, canonical_url = cls.parse_metadata(soup)
        title = page_title or clean_text(soup.title.get_text() if soup.title else "")

        snippets: List[str] = []
        if title:
            snippets.append(f"PAGE_TITLE: {title}")

        h1 = soup.find("h1")
        if h1 and clean_text(h1.get_text()):
            snippets.append(f"HEADING_H1: {clean_text(h1.get_text())}")

        # Price quote snippet
        price_el = soup.find(class_=re.compile(r"price", re.I))
        if price_el and clean_text(price_el.get_text()):
            snippets.append(f"PRICE_SNIPPET: {clean_text(price_el.get_text())}")

        # Meta description snippet
        if meta_tags.get("description"):
            snippets.append(f"META_DESCRIPTION: {meta_tags['description']}")

        # Up to 4 key specification snippets
        specs = cls.parse_specifications_table(soup)
        for k, v in list(specs.items())[:4]:
            snippets.append(f"SPECIFICATION: {k} = {v}")

        # Compute SHA-256 hash over canonical evidence JSON
        canonical_record = {
            "source_url": source_url,
            "capture_timestamp_utc": timestamp,
            "page_title": title,
            "canonical_url": canonical_url,
            "extracted_text_snippets": snippets,
        }
        canonical_bytes = json.dumps(canonical_record, sort_keys=True).encode("utf-8")
        evidence_hash = hashlib.sha256(canonical_bytes).hexdigest()

        return PageEvidenceRecordResult(
            source_url=source_url,
            capture_timestamp_utc=timestamp,
            page_title=title,
            canonical_url=canonical_url,
            extracted_text_snippets=snippets,
            sha256_hash=evidence_hash,
            content_length_bytes=len(html_content.encode("utf-8")),
        )

    @classmethod
    def inspect_metadata(
        cls, html_content: str, source_url: str, final_url: str, page_title: Optional[str]
    ) -> PageMetadataResult:
        """Inspect all page metadata, canonical links, and detected schema types."""
        timestamp = current_utc_iso()
        if not html_content:
            return PageMetadataResult(
                source_url=source_url,
                final_url=final_url,
                title=page_title,
                capture_timestamp_utc=timestamp,
                error="Empty HTML content",
            )

        soup = BeautifulSoup(html_content, "html.parser")
        open_graph, meta_tags, canonical_url = cls.parse_metadata(soup)
        _, detected_types = cls.parse_json_ld(soup)

        combined_metadata = {**meta_tags, **open_graph}
        title = page_title or clean_text(soup.title.get_text() if soup.title else "")

        return PageMetadataResult(
            source_url=source_url,
            final_url=final_url,
            canonical_url=canonical_url,
            title=title,
            page_metadata=combined_metadata,
            detected_structured_data_types=detected_types,
            capture_timestamp_utc=timestamp,
        )
