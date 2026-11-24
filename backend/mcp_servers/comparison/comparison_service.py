import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp_servers.comparison.normalization import (
    extract_model_number,
    generate_configuration_fingerprint,
    normalize_brand,
    normalize_cpu,
    normalize_gpu,
    normalize_ram,
    normalize_screen_size,
    normalize_storage,
)
from mcp_servers.comparison.schemas import (
    ComprehensiveComparisonResult,
    NormalizedProduct,
    NormalizedSpecField,
    PolicyComparisonResult,
    PolicyItem,
    PriceComparisonResult,
    PricePoint,
    ProductConflictItem,
    ProductConflictResult,
    SpecComparisonItem,
    SpecComparisonResult,
    current_utc_iso,
)

logger = logging.getLogger("webtruth.comparison.service")


def get_domain(url: Optional[str]) -> str:
    """Extract domain host safely."""
    if not url:
        return "unknown"
    if url.startswith("file://"):
        return "local_fixture"
    try:
        p = urlparse(url)
        return (p.hostname or "unknown").lower()
    except Exception:
        return "unknown"


class ComparisonService:
    """Deterministic product comparison and conflict detection service."""

    def normalize_product(
        self,
        product_name: str,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        specifications: Optional[Dict[str, str]] = None,
        source_evidence_id: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> NormalizedProduct:
        """Normalize product specifications while retaining original raw values."""
        specs = specifications or {}

        # 1. Brand
        raw_b, norm_b = normalize_brand(brand or specs.get("Brand") or specs.get("Manufacturer"))
        brand_field = NormalizedSpecField(
            field_name="brand",
            raw_value=raw_b,
            normalized_value=norm_b,
        )

        # 2. Model & Model Number
        raw_m = model or specs.get("Model") or specs.get("Model Name")
        model_num = extract_model_number(raw_m, product_name)
        model_field = NormalizedSpecField(
            field_name="model",
            raw_value=raw_m,
            normalized_value=raw_m.strip() if raw_m else None,
        )
        model_num_field = (
            NormalizedSpecField(
                field_name="model_number",
                raw_value=model_num,
                normalized_value=model_num,
            )
            if model_num
            else None
        )

        # 3. RAM
        raw_ram = (
            specs.get("RAM")
            or specs.get("Memory")
            or specs.get("System Memory")
            or specs.get("Installed RAM")
        )
        ram_dict = normalize_ram(raw_ram)
        ram_field = (
            NormalizedSpecField(
                field_name="ram",
                raw_value=ram_dict["raw_value"],
                normalized_value=ram_dict["normalized_value"],
                numeric_value=ram_dict["numeric_value"],
                unit=ram_dict["unit"],
            )
            if ram_dict["raw_value"]
            else None
        )

        # 4. Storage
        raw_storage = (
            specs.get("Storage")
            or specs.get("Hard Drive")
            or specs.get("SSD Capacity")
            or specs.get("Internal Storage")
        )
        stor_dict = normalize_storage(raw_storage)
        storage_field = (
            NormalizedSpecField(
                field_name="storage",
                raw_value=stor_dict["raw_value"],
                normalized_value=stor_dict["normalized_value"],
                numeric_value=stor_dict["numeric_value"],
                unit=stor_dict["unit"],
            )
            if stor_dict["raw_value"]
            else None
        )

        # 5. CPU
        raw_cpu = (
            specs.get("CPU")
            or specs.get("Processor")
            or specs.get("Processor Model")
            or specs.get("Processor Type")
        )
        cpu_dict = normalize_cpu(raw_cpu)
        cpu_field = (
            NormalizedSpecField(
                field_name="cpu",
                raw_value=cpu_dict["raw_value"],
                normalized_value=cpu_dict["normalized_value"],
            )
            if cpu_dict["raw_value"]
            else None
        )

        # 6. GPU
        raw_gpu = (
            specs.get("GPU")
            or specs.get("Graphics Card")
            or specs.get("Graphics")
            or specs.get("Video Card")
        )
        gpu_dict = normalize_gpu(raw_gpu)
        gpu_field = (
            NormalizedSpecField(
                field_name="gpu",
                raw_value=gpu_dict["raw_value"],
                normalized_value=gpu_dict["normalized_value"],
            )
            if gpu_dict["raw_value"]
            else None
        )

        # 7. Screen Size
        raw_screen = (
            specs.get("Display")
            or specs.get("Screen")
            or specs.get("Screen Size")
            or specs.get("Display Size")
        )
        screen_dict = normalize_screen_size(raw_screen)
        screen_field = (
            NormalizedSpecField(
                field_name="screen_size",
                raw_value=screen_dict["raw_value"],
                normalized_value=screen_dict["normalized_value"],
                numeric_value=screen_dict["diagonal_inches"],
                unit='"' if screen_dict["diagonal_inches"] else None,
            )
            if screen_dict["raw_value"]
            else None
        )

        # 8. Other specs
        other_specs: Dict[str, NormalizedSpecField] = {}
        for k, v in specs.items():
            if k.lower() not in (
                "brand", "manufacturer", "model", "ram", "memory", "storage",
                "cpu", "processor", "gpu", "graphics", "display", "screen",
            ):
                other_specs[k] = NormalizedSpecField(
                    field_name=k,
                    raw_value=str(v),
                    normalized_value=str(v).strip(),
                )

        # 9. Deterministic config fingerprint
        fingerprint = generate_configuration_fingerprint(
            brand=norm_b,
            model=raw_m,
            model_number=model_num,
            cpu=cpu_dict["chip_code"] or cpu_dict["normalized_value"],
            ram_gb=ram_dict["numeric_value"],
            storage_gb=stor_dict["numeric_value"],
            gpu=gpu_dict["model"] or gpu_dict["normalized_value"],
        )

        return NormalizedProduct(
            product_name=product_name,
            brand=brand_field,
            model=model_field,
            model_number=model_num_field,
            ram=ram_field,
            storage=storage_field,
            cpu=cpu_field,
            gpu=gpu_field,
            screen_size=screen_field,
            other_specs=other_specs,
            config_fingerprint=fingerprint,
            source_evidence_id=source_evidence_id,
            source_url=source_url,
        )

    def compare_prices(
        self,
        price_records: List[Dict[str, Any]],
        exchange_rates: Optional[Dict[str, float]] = None,
    ) -> PriceComparisonResult:
        """Compare actual displayed product prices across evidence records.
        
        Preserves raw price text, currency, source URL and capture timestamp.
        Only calculates numeric differences when currencies match and numeric values are available.
        Never invents missing prices or performs unauthenticated currency conversions.
        """
        price_points: List[PricePoint] = []
        currencies_found: set[str] = set()
        missing_sources: List[str] = []
        notes: List[str] = []

        for rec in price_records:
            url = rec.get("source_url") or "unknown"
            domain = rec.get("source_domain") or get_domain(url)
            displayed = rec.get("raw_displayed_price")
            curr = rec.get("currency")
            num = rec.get("numeric_price")
            evi_id = rec.get("evidence_id")
            ts = rec.get("capture_timestamp") or current_utc_iso()

            pt = PricePoint(
                source_url=url,
                source_domain=domain,
                source_title=rec.get("source_title"),
                capture_timestamp=ts,
                raw_displayed_price=displayed,
                currency=curr,
                numeric_price=num,
                evidence_id=evi_id,
            )
            price_points.append(pt)

            if curr:
                currencies_found.add(curr.upper())

            if displayed is None and num is None:
                missing_sources.append(url)

        unique_currencies = sorted(list(currencies_found))
        currency_mismatch = len(unique_currencies) > 1

        lowest_pt: Optional[PricePoint] = None
        highest_pt: Optional[PricePoint] = None
        price_spread: Optional[float] = None

        if currency_mismatch:
            notes.append(
                f"Currencies mismatch: found {', '.join(unique_currencies)}. "
                "Numeric price spread calculation suppressed to prevent inaccurate conversion."
            )
        else:
            valid_pts = [p for p in price_points if p.numeric_price is not None]
            if valid_pts:
                valid_pts.sort(key=lambda p: p.numeric_price)  # type: ignore
                lowest_pt = valid_pts[0]
                highest_pt = valid_pts[-1]
                if highest_pt.numeric_price is not None and lowest_pt.numeric_price is not None:
                    price_spread = round(highest_pt.numeric_price - lowest_pt.numeric_price, 2)
                    notes.append(
                        f"Spread between highest ({highest_pt.numeric_price:,.0f} {highest_pt.currency or ''}) "
                        f"and lowest ({lowest_pt.numeric_price:,.0f} {lowest_pt.currency or ''}) is "
                        f"{price_spread:,.0f} {lowest_pt.currency or ''}."
                    )
            else:
                notes.append("No verified numeric prices available across supplied sources.")

        if missing_sources:
            notes.append(f"{len(missing_sources)} source(s) had no displayed price.")

        return PriceComparisonResult(
            total_sources=len(price_points),
            price_points=price_points,
            lowest_price=lowest_pt,
            highest_price=highest_pt,
            price_spread=price_spread,
            currency_mismatch_detected=currency_mismatch,
            currencies_found=unique_currencies,
            missing_price_sources=missing_sources,
            comparison_notes=notes,
        )

    def compare_specifications(self, products: List[NormalizedProduct]) -> SpecComparisonResult:
        """Compare specifications across normalized products.
        
        Identifies equal, different and unavailable fields without inventing data.
        """
        if not products:
            return SpecComparisonResult(
                equal_fields=[],
                different_fields=[],
                unavailable_fields=[],
                total_fields_compared=0,
                configuration_match=True,
            )

        # Standard core fields to scrutinize
        core_keys = ["brand", "model", "model_number", "cpu", "ram", "storage", "gpu", "screen_size"]

        equal_items: List[SpecComparisonItem] = []
        diff_items: List[SpecComparisonItem] = []
        unavail_items: List[SpecComparisonItem] = []

        all_fields = list(core_keys)
        # Collect any other spec keys present across all products
        for p in products:
            for k in p.other_specs.keys():
                if k not in all_fields:
                    all_fields.append(k)

        for field in all_fields:
            values_map: Dict[str, Optional[str]] = {}
            evi_ids: List[str] = []

            for idx, prod in enumerate(products):
                label = prod.source_domain if hasattr(prod, "source_domain") else get_domain(prod.source_url)
                if label == "unknown":
                    label = f"Source {idx + 1}"
                
                # Retrieve field value
                val_obj: Optional[NormalizedSpecField] = None
                if field in core_keys:
                    val_obj = getattr(prod, field, None)
                else:
                    val_obj = prod.other_specs.get(field)

                val_str = val_obj.normalized_value if val_obj else None
                values_map[label] = val_str
                if prod.source_evidence_id:
                    evi_ids.append(prod.source_evidence_id)

            unique_values = {v for v in values_map.values() if v is not None}
            has_none = any(v is None for v in values_map.values())

            if len(unique_values) == 0:
                # Completely unavailable across all sources
                unavail_items.append(
                    SpecComparisonItem(
                        field_name=field,
                        status="unavailable",
                        values_by_source=values_map,
                        evidence_ids=list(dict.fromkeys(evi_ids)),
                        note="Field missing across all scrutinized sources",
                    )
                )
            elif has_none:
                # Available on some, missing on others
                missing_from = [k for k, v in values_map.items() if v is None]
                unavail_items.append(
                    SpecComparisonItem(
                        field_name=field,
                        status="unavailable",
                        values_by_source=values_map,
                        evidence_ids=list(dict.fromkeys(evi_ids)),
                        note=f"Disclosed by some sources but missing from: {', '.join(missing_from)}",
                    )
                )
            elif len(unique_values) == 1:
                # All disclosed values match
                equal_items.append(
                    SpecComparisonItem(
                        field_name=field,
                        status="equal",
                        values_by_source=values_map,
                        evidence_ids=list(dict.fromkeys(evi_ids)),
                        note="Consistent across all sources",
                    )
                )
            else:
                # Disclosed values contradict
                diff_items.append(
                    SpecComparisonItem(
                        field_name=field,
                        status="different",
                        values_by_source=values_map,
                        evidence_ids=list(dict.fromkeys(evi_ids)),
                        note="Conflicting values detected across sources",
                    )
                )

        # Verify whether hardware configurations are identical
        fingerprints = {p.config_fingerprint for p in products}
        config_match = len(fingerprints) <= 1

        return SpecComparisonResult(
            equal_fields=equal_items,
            different_fields=diff_items,
            unavailable_fields=unavail_items,
            total_fields_compared=len(all_fields),
            configuration_match=config_match,
        )

    def compare_policies(self, policy_records: List[Dict[str, Any]]) -> PolicyComparisonResult:
        """Compare warranty, return, replacement, and delivery terms across sources."""
        items: List[PolicyItem] = []
        missing_count = 0

        for rec in policy_records:
            url = rec.get("source_url") or "unknown"
            domain = rec.get("source_domain") or get_domain(url)
            evi_id = rec.get("evidence_id")

            # Check warranty
            w = rec.get("warranty")
            if not w or not str(w).strip():
                items.append(
                    PolicyItem(
                        policy_type="warranty",
                        source_url=url,
                        source_domain=domain,
                        evidence_id=evi_id,
                        raw_terms=None,
                        is_missing=True,
                        is_ambiguous=False,
                    )
                )
                missing_count += 1
            else:
                w_str = str(w).strip()
                is_ambig = bool(re.search(r"standard|applicable|contact seller|t&c", w_str, re.I))
                items.append(
                    PolicyItem(
                        policy_type="warranty",
                        source_url=url,
                        source_domain=domain,
                        evidence_id=evi_id,
                        raw_terms=w_str,
                        is_missing=False,
                        is_ambiguous=is_ambig,
                    )
                )

            # Check return / replacement policy
            ret = rec.get("return_policy") or rec.get("returns")
            if not ret or not str(ret).strip():
                items.append(
                    PolicyItem(
                        policy_type="returns",
                        source_url=url,
                        source_domain=domain,
                        evidence_id=evi_id,
                        raw_terms=None,
                        is_missing=True,
                        is_ambiguous=False,
                    )
                )
                missing_count += 1
            else:
                r_str = str(ret).strip()
                is_ambig = bool(re.search(r"conditions apply|per store policy", r_str, re.I))
                items.append(
                    PolicyItem(
                        policy_type="returns",
                        source_url=url,
                        source_domain=domain,
                        evidence_id=evi_id,
                        raw_terms=r_str,
                        is_missing=False,
                        is_ambiguous=is_ambig,
                    )
                )

        summary = (
            f"Audited {len(policy_records)} source policy sets. "
            f"Found {missing_count} missing policy disclosure(s)."
        )

        return PolicyComparisonResult(
            policies=items,
            missing_policies_count=missing_count,
            summary=summary,
        )

    def find_product_conflicts(
        self,
        products: List[NormalizedProduct],
        policy_records: Optional[List[Dict[str, Any]]] = None,
    ) -> ProductConflictResult:
        """Detect and isolate factual contradictions across sources."""
        conflicts: List[ProductConflictItem] = []

        # Check core hardware conflicts
        spec_result = self.compare_specifications(products)
        for diff in spec_result.different_fields:
            claims_list = []
            for src, val in diff.values_by_source.items():
                matching_p = next(
                    (p for p in products if (p.source_url == src or get_domain(p.source_url) == src)),
                    None,
                )
                claims_list.append({
                    "source": src,
                    "claimed_value": val,
                    "evidence_id": matching_p.source_evidence_id if matching_p else None,
                    "source_url": matching_p.source_url if matching_p else None,
                })

            conflicts.append(
                ProductConflictItem(
                    field_name=diff.field_name,
                    conflict_description=(
                        f"Dispute on '{diff.field_name}': multiple sources report conflicting "
                        f"claims ({', '.join(str(c['claimed_value']) for c in claims_list)})."
                    ),
                    claims=claims_list,
                )
            )

        # Check policy conflicts if policy records provided
        if policy_records and len(policy_records) > 1:
            warranties = {
                (r.get("source_domain") or get_domain(r.get("source_url"))): r.get("warranty")
                for r in policy_records
                if r.get("warranty")
            }
            if len(set(warranties.values())) > 1:
                claims_list = [
                    {
                        "source": src,
                        "claimed_value": w,
                        "evidence_id": next((r.get("evidence_id") for r in policy_records if (r.get("source_domain") == src or get_domain(r.get("source_url")) == src)), None),
                    }
                    for src, w in warranties.items()
                ]
                conflicts.append(
                    ProductConflictItem(
                        field_name="warranty",
                        conflict_description="Differing warranty terms declared by retailers.",
                        claims=claims_list,
                    )
                )

        return ProductConflictResult(
            has_conflicts=len(conflicts) > 0,
            conflicts_count=len(conflicts),
            conflicts=conflicts,
        )

    def generate_comparison(self, evidence_items: List[Dict[str, Any]]) -> ComprehensiveComparisonResult:
        """Synthesize a complete structured comparison across evidence records."""
        if not evidence_items:
            raise ValueError("Cannot generate comparison on empty evidence list.")

        # 1. Normalize each item
        normalized_prods: List[NormalizedProduct] = []
        price_recs: List[Dict[str, Any]] = []
        policy_recs: List[Dict[str, Any]] = []
        all_evi_refs: List[str] = []

        for item in evidence_items:
            evi_id = item.get("evidence_id")
            url = item.get("source_url") or "unknown"
            if evi_id:
                all_evi_refs.append(evi_id)

            # Specs normalization
            specs = item.get("specifications") or {}
            # Fallback: if specs is empty, extract from extracted_claims if present
            if not specs and item.get("extracted_claims"):
                claims = item["extracted_claims"]
                for c in claims:
                    if "=" in c:
                        k, v = c.split("=", 1)
                        specs[k.strip()] = v.strip()
                    elif ":" in c:
                        k, v = c.split(":", 1)
                        specs[k.strip()] = v.strip()

            p = self.normalize_product(
                product_name=item.get("product_name") or item.get("source_title") or "Unknown Product",
                brand=item.get("brand"),
                model=item.get("model"),
                specifications=specs,
                source_evidence_id=evi_id,
                source_url=url,
            )
            normalized_prods.append(p)

            # Price record
            price_recs.append({
                "source_url": url,
                "source_domain": item.get("source_domain") or get_domain(url),
                "source_title": item.get("source_title"),
                "capture_timestamp": item.get("capture_timestamp") or current_utc_iso(),
                "raw_displayed_price": item.get("raw_displayed_price"),
                "currency": item.get("currency"),
                "numeric_price": item.get("numeric_price"),
                "evidence_id": evi_id,
            })

            # Policy record
            policy_recs.append({
                "source_url": url,
                "source_domain": item.get("source_domain") or get_domain(url),
                "evidence_id": evi_id,
                "warranty": item.get("warranty"),
                "return_policy": item.get("return_policy"),
            })

        # 2. Run component comparisons
        price_res = self.compare_prices(price_recs)
        spec_res = self.compare_specifications(normalized_prods)
        policy_res = self.compare_policies(policy_recs)
        conflict_res = self.find_product_conflicts(normalized_prods, policy_recs)

        # 3. Model number & configuration mismatch warnings
        warnings: List[str] = []
        model_numbers = {
            p.model_number.normalized_value
            for p in normalized_prods
            if p.model_number and p.model_number.normalized_value
        }
        if len(model_numbers) > 1:
            warnings.append(
                f"Configuration alert: Multiple model numbers detected ({', '.join(model_numbers)}). "
                "These products may represent different hardware revisions or generations."
            )

        if not spec_res.configuration_match:
            warnings.append(
                "Hardware configuration mismatch detected (RAM, Storage, CPU, or GPU capacities differ). "
                "Sources are not describing an identical configuration."
            )

        # 4. Unknown fields (missing across all sources)
        unknown_fields = [
            item.field_name for item in spec_res.unavailable_fields
            if "missing across all" in (item.note or "")
        ]

        # 5. Product identity summary
        canonical_brand = next((p.brand.normalized_value for p in normalized_prods if p.brand.normalized_value), "Unknown")
        canonical_model = next((p.model.normalized_value for p in normalized_prods if p.model.normalized_value), "Unknown")

        identity = {
            "canonical_name": normalized_prods[0].product_name,
            "brand": canonical_brand,
            "model": canonical_model,
            "model_numbers": list(model_numbers),
            "configuration_fingerprints": list({p.config_fingerprint for p in normalized_prods}),
        }

        return ComprehensiveComparisonResult(
            product_identity=identity,
            configuration_match=spec_res.configuration_match and len(model_numbers) <= 1,
            configuration_warnings=warnings,
            price_comparison=price_res,
            spec_comparison=spec_res,
            policy_comparison=policy_res,
            conflicts=conflict_res,
            unknown_fields=unknown_fields,
            evidence_references=list(dict.fromkeys(all_evi_refs)),
        )


# Global singleton instance
comparison_service = ComparisonService()
