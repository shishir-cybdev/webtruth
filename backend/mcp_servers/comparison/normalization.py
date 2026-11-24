import re
from typing import Any, Dict, Optional, Tuple

KNOWN_BRANDS = {
    "dell": "Dell",
    "apple": "Apple",
    "lenovo": "Lenovo",
    "asus": "ASUS",
    "hp": "HP",
    "hewlett-packard": "HP",
    "sony": "Sony",
    "samsung": "Samsung",
    "acer": "Acer",
    "msi": "MSI",
    "microsoft": "Microsoft",
    "lg": "LG",
}


def normalize_brand(raw_brand: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Normalize brand name to canonical casing while preserving raw string.
    
    Returns: (raw_brand, normalized_brand)
    """
    if not raw_brand or not str(raw_brand).strip():
        return None, None
    raw = str(raw_brand).strip()
    key = raw.lower()
    normalized = KNOWN_BRANDS.get(key, raw.title())
    return raw, normalized


def normalize_ram(raw_ram: Optional[str]) -> Dict[str, Any]:
    """Parse and normalize RAM capacity, unit, and memory technology.
    
    Returns dict:
      raw_value: original text
      normalized_value: formatted canonical string (e.g. '16 GB DDR5')
      numeric_value: integer gigabytes (e.g. 16.0)
      unit: 'GB'
      memory_type: 'DDR5', 'LPDDR5', 'Unified', etc.
    """
    if not raw_ram or not str(raw_ram).strip():
        return {
            "raw_value": None,
            "normalized_value": None,
            "numeric_value": None,
            "unit": None,
            "memory_type": None,
        }

    raw = str(raw_ram).strip()
    capacity_gb: Optional[float] = None
    mem_type: Optional[str] = None

    # Match capacity (e.g., '16 GB', '16GB', '32G')
    match = re.search(r"(\d+)\s*(GB|TB|G)\b", raw, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        unit = match.group(2).upper()
        if unit == "TB":
            capacity_gb = val * 1024
        else:
            capacity_gb = val

    # Match memory technology
    type_match = re.search(
        r"\b(LPDDR5X|LPDDR5|LPDDR4X|DDR5|DDR4|Unified)\b", raw, re.IGNORECASE
    )
    if type_match:
        mem_type = type_match.group(1).upper()
        if mem_type == "UNIFIED":
            mem_type = "Unified"

    parts = []
    if capacity_gb is not None:
        parts.append(f"{int(capacity_gb)} GB")
    if mem_type:
        parts.append(mem_type)

    normalized = " ".join(parts) if parts else raw

    return {
        "raw_value": raw,
        "normalized_value": normalized if normalized else None,
        "numeric_value": capacity_gb,
        "unit": "GB" if capacity_gb is not None else None,
        "memory_type": mem_type,
    }


def normalize_storage(raw_storage: Optional[str]) -> Dict[str, Any]:
    """Parse and normalize storage capacity into GB with media type (SSD/HDD)."""
    if not raw_storage or not str(raw_storage).strip():
        return {
            "raw_value": None,
            "normalized_value": None,
            "numeric_value": None,
            "unit": None,
            "storage_type": None,
        }

    raw = str(raw_storage).strip()
    capacity_gb: Optional[float] = None
    storage_type: Optional[str] = None

    match = re.search(r"(\d+(?:\.\d+)?)\s*(GB|TB|G)\b", raw, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        unit = match.group(2).upper()
        if unit == "TB":
            capacity_gb = val * 1024
        else:
            capacity_gb = val

    if re.search(r"\bNVMe\b", raw, re.IGNORECASE):
        storage_type = "NVMe SSD"
    elif re.search(r"\bSSD\b", raw, re.IGNORECASE):
        storage_type = "SSD"
    elif re.search(r"\bHDD\b|\bHard Drive\b", raw, re.IGNORECASE):
        storage_type = "HDD"

    parts = []
    if capacity_gb is not None:
        if capacity_gb >= 1024 and capacity_gb % 1024 == 0:
            parts.append(f"{int(capacity_gb // 1024)} TB")
        else:
            parts.append(f"{int(capacity_gb)} GB")
    if storage_type:
        parts.append(storage_type)

    normalized = " ".join(parts) if parts else raw

    return {
        "raw_value": raw,
        "normalized_value": normalized if normalized else None,
        "numeric_value": capacity_gb,
        "unit": "GB" if capacity_gb is not None else None,
        "storage_type": storage_type,
    }


def normalize_cpu(raw_cpu: Optional[str]) -> Dict[str, Any]:
    """Parse CPU into canonical vendor, tier, and specific model number."""
    if not raw_cpu or not str(raw_cpu).strip():
        return {
            "raw_value": None,
            "normalized_value": None,
            "vendor": None,
            "tier": None,
            "chip_code": None,
        }

    raw = str(raw_cpu).strip()
    vendor: Optional[str] = None
    tier: Optional[str] = None
    chip_code: Optional[str] = None

    if re.search(r"\bIntel\b", raw, re.IGNORECASE):
        vendor = "Intel"
        tier_m = re.search(r"(Core\s+(?:Ultra\s+)?[iI][3579]|Xeon)", raw, re.IGNORECASE)
        if tier_m:
            tier = re.sub(r"\s+", " ", tier_m.group(1)).title()
        code_m = re.search(r"\b(\d{4,5}[A-Z]{0,2}|[12]\d{2}[HUK])\b", raw)
        if code_m:
            chip_code = code_m.group(1)
    elif re.search(r"\bAMD\b|\bRyzen\b", raw, re.IGNORECASE):
        vendor = "AMD"
        tier_m = re.search(r"Ryzen\s+[3579](?:\s+PRO)?", raw, re.IGNORECASE)
        if tier_m:
            tier = re.sub(r"\s+", " ", tier_m.group(0)).title()
        code_m = re.search(r"\b(\d{4}[A-Z]{1,2})\b", raw)
        if code_m:
            chip_code = code_m.group(1)
    elif re.search(r"\bApple\b|\bM[1234]\b", raw, re.IGNORECASE):
        vendor = "Apple"
        m_match = re.search(r"M[1234](?:\s+(?:Pro|Max|Ultra))?", raw, re.IGNORECASE)
        if m_match:
            tier = m_match.group(0)
            chip_code = m_match.group(0)

    parts = [p for p in [vendor, tier, chip_code] if p]
    normalized = " ".join(dict.fromkeys(parts)) if parts else raw

    return {
        "raw_value": raw,
        "normalized_value": normalized if normalized else None,
        "vendor": vendor,
        "tier": tier,
        "chip_code": chip_code,
    }


def normalize_gpu(raw_gpu: Optional[str]) -> Dict[str, Any]:
    """Parse GPU into vendor, series, and VRAM."""
    if not raw_gpu or not str(raw_gpu).strip():
        return {
            "raw_value": None,
            "normalized_value": None,
            "vendor": None,
            "model": None,
            "vram": None,
        }

    raw = str(raw_gpu).strip()
    vendor: Optional[str] = None
    model: Optional[str] = None
    vram: Optional[str] = None

    if re.search(r"\bNVIDIA\b|\bGeForce\b|\bRTX\b|\bGTX\b", raw, re.IGNORECASE):
        vendor = "NVIDIA"
        m = re.search(r"(?:RTX|GTX)\s+\d{4}(?:\s*Ti)?", raw, re.IGNORECASE)
        if m:
            model = m.group(0).upper()
        vram_m = re.search(r"(\d+\s*GB)", raw, re.IGNORECASE)
        if vram_m:
            vram = vram_m.group(1).upper()
    elif re.search(r"\bIntel\b|\bIris\b|\bArc\b", raw, re.IGNORECASE):
        vendor = "Intel"
        m = re.search(r"(Iris\s+X[eE]|Arc\s+[A-Za-z0-9]+)", raw, re.IGNORECASE)
        if m:
            model = m.group(0)
    elif re.search(r"\bApple\b", raw, re.IGNORECASE) or re.search(r"\bGPU\b", raw, re.IGNORECASE):
        vendor = "Apple"
        m = re.search(r"\d+-core\s+GPU", raw, re.IGNORECASE)
        if m:
            model = m.group(0)

    parts = [p for p in [vendor, model, vram] if p]
    normalized = " ".join(dict.fromkeys(parts)) if parts else raw

    return {
        "raw_value": raw,
        "normalized_value": normalized if normalized else None,
        "vendor": vendor,
        "model": model,
        "vram": vram,
    }


def normalize_screen_size(raw_screen: Optional[str]) -> Dict[str, Any]:
    """Parse screen diagonal and display panel type."""
    if not raw_screen or not str(raw_screen).strip():
        return {
            "raw_value": None,
            "normalized_value": None,
            "diagonal_inches": None,
            "display_type": None,
        }

    raw = str(raw_screen).strip()
    diagonal: Optional[float] = None
    display_type: Optional[str] = None

    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\"|inch|\-inch|in\b)", raw, re.IGNORECASE)
    if m:
        diagonal = float(m.group(1))

    if re.search(r"\bOLED\b", raw, re.IGNORECASE):
        display_type = "OLED"
    elif re.search(r"\bMini[\s\-]LED\b", raw, re.IGNORECASE):
        display_type = "Mini-LED"
    elif re.search(r"\bIPS\b", raw, re.IGNORECASE):
        display_type = "IPS"

    parts = []
    if diagonal is not None:
        parts.append(f'{diagonal}"')
    if display_type:
        parts.append(display_type)

    normalized = " ".join(parts) if parts else raw

    return {
        "raw_value": raw,
        "normalized_value": normalized if normalized else None,
        "diagonal_inches": diagonal,
        "display_type": display_type,
    }


def extract_model_number(model_str: Optional[str], product_name: Optional[str]) -> Optional[str]:
    """Extract model suffix / number (e.g. '9530', 'GA402', 'Gen 11', 'M3 Pro')."""
    candidates = [s for s in (model_str, product_name) if s]
    for text in candidates:
        # Pattern 1: 4-digit model code like 9530, 9520, 7960
        m = re.search(r"\b(\d{4}[A-Za-z]?)\b", text)
        if m:
            return m.group(1).upper()
        # Pattern 2: Generation marker like Gen 11, G14
        m_gen = re.search(r"\b(Gen\s+\d+|G\d{2})\b", text, re.IGNORECASE)
        if m_gen:
            return re.sub(r"\s+", " ", m_gen.group(1)).title()
        # Pattern 3: Alpha-numeric product code (e.g., GA402XY)
        m_code = re.search(r"\b([A-Z]{2}\d{3}[A-Z0-9]{1,3})\b", text)
        if m_code:
            return m_code.group(1).upper()
    return None


def generate_configuration_fingerprint(
    brand: Optional[str],
    model: Optional[str],
    model_number: Optional[str],
    cpu: Optional[str],
    ram_gb: Optional[float],
    storage_gb: Optional[float],
    gpu: Optional[str],
) -> str:
    """Generate a deterministic fingerprint identifying this specific configuration variant.
    
    If model numbers, RAM, or storage differ, the configuration fingerprint WILL differ.
    This guarantees that different product configurations are never falsely equated.
    """
    components = [
        (brand or "unknown").strip().lower(),
        (model or "unknown").strip().lower(),
        (model_number or "base").strip().lower(),
        (cpu or "unspecified-cpu").strip().lower(),
        f"{int(ram_gb)}gb" if ram_gb is not None else "unspecified-ram",
        f"{int(storage_gb)}gb" if storage_gb is not None else "unspecified-storage",
        (gpu or "unspecified-gpu").strip().lower(),
    ]
    # Clean characters
    cleaned = [re.sub(r"[^a-z0-9\-]+", "-", c).strip("-") for c in components]
    return "|".join(cleaned)
