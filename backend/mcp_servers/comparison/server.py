import logging
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from mcp_servers.comparison.comparison_service import comparison_service
from mcp_servers.comparison.schemas import (
    ComprehensiveComparisonResult,
    NormalizedProduct,
    PolicyComparisonResult,
    PriceComparisonResult,
    ProductConflictResult,
    SpecComparisonResult,
)

logger = logging.getLogger("webtruth.comparison.mcp")

# Initialize Comparison MCP Server instance
server = MCPServer(
    name="webtruth-comparison",
    instructions=(
        "WebTruth Comparison MCP Server (Phase 2D). Provides deterministic specification normalization, "
        "evidence-backed price comparison (without unauthenticated currency conversion), conflict "
        "detection, policy auditing, and comprehensive multi-retailer synthesis."
    ),
    version="0.2.0-phase2d",
)


@server.tool(
    name="normalize_product",
    description=(
        "Normalize brand, model, model number, RAM, storage, CPU, GPU, screen size and other supplied "
        "specifications. Preserves original values alongside normalized values and computes a configuration fingerprint."
    ),
)
async def normalize_product(
    product_name: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    specifications: Optional[Dict[str, str]] = None,
    source_evidence_id: Optional[str] = None,
    source_url: Optional[str] = None,
) -> NormalizedProduct:
    """Normalize a product's hardware attributes while preserving raw strings."""
    return comparison_service.normalize_product(
        product_name=product_name,
        brand=brand,
        model=model,
        specifications=specifications or {},
        source_evidence_id=source_evidence_id,
        source_url=source_url,
    )


@server.tool(
    name="compare_prices",
    description=(
        "Compare actual displayed product prices across evidence records. Preserves raw price text, "
        "currency, source URL and timestamp. Only calculates numeric differences when currencies match. "
        "Never invents missing prices."
    ),
)
async def compare_prices(
    price_records: List[Dict[str, Any]],
    exchange_rates: Optional[Dict[str, float]] = None,
) -> PriceComparisonResult:
    """Compare product prices across sources without unauthorized currency conversion."""
    return comparison_service.compare_prices(
        price_records=price_records,
        exchange_rates=exchange_rates,
    )


@server.tool(
    name="compare_specifications",
    description=(
        "Compare specifications between matching products. Identifies equal, different and unavailable fields, "
        "and checks whether underlying hardware configurations match."
    ),
)
async def compare_specifications(
    products: List[Dict[str, Any]],
) -> SpecComparisonResult:
    """Compare specifications across multiple product definitions."""
    norm_prods: List[NormalizedProduct] = []
    for item in products:
        if isinstance(item, NormalizedProduct):
            norm_prods.append(item)
        elif isinstance(item, dict) and "config_fingerprint" in item:
            norm_prods.append(NormalizedProduct(**item))
        else:
            norm_prods.append(
                comparison_service.normalize_product(
                    product_name=item.get("product_name") or "Product",
                    brand=item.get("brand"),
                    model=item.get("model"),
                    specifications=item.get("specifications") or {},
                    source_evidence_id=item.get("source_evidence_id"),
                    source_url=item.get("source_url"),
                )
            )
    return comparison_service.compare_specifications(norm_prods)


@server.tool(
    name="compare_policies",
    description=(
        "Compare available warranty, returns, replacement and delivery terms across sources. "
        "Preserves source references and flags missing or ambiguous disclosures."
    ),
)
async def compare_policies(
    policy_records: List[Dict[str, Any]],
) -> PolicyComparisonResult:
    """Compare warranty and store policy terms across retailers."""
    return comparison_service.compare_policies(policy_records)


@server.tool(
    name="find_product_conflicts",
    description=(
        "Detect conflicting claims for the same product field across sources. "
        "Returns both claims along with their source URLs and evidence IDs."
    ),
)
async def find_product_conflicts(
    products: List[Dict[str, Any]],
    policy_records: Optional[List[Dict[str, Any]]] = None,
) -> ProductConflictResult:
    """Detect factual contradictions across sources for a product."""
    norm_prods: List[NormalizedProduct] = []
    for item in products:
        if isinstance(item, NormalizedProduct):
            norm_prods.append(item)
        elif isinstance(item, dict) and "config_fingerprint" in item:
            norm_prods.append(NormalizedProduct(**item))
        else:
            norm_prods.append(
                comparison_service.normalize_product(
                    product_name=item.get("product_name") or "Product",
                    brand=item.get("brand"),
                    model=item.get("model"),
                    specifications=item.get("specifications") or {},
                    source_evidence_id=item.get("source_evidence_id"),
                    source_url=item.get("source_url"),
                )
            )
    return comparison_service.find_product_conflicts(norm_prods, policy_records)


@server.tool(
    name="generate_comparison",
    description=(
        "Produce a complete structured comparison containing product identity, prices, specification "
        "differences, policy differences, conflicts, unknown fields, and evidence references."
    ),
)
async def generate_comparison(
    evidence_items: List[Dict[str, Any]],
) -> ComprehensiveComparisonResult:
    """Generate a comprehensive multi-source investigation comparison."""
    return comparison_service.generate_comparison(evidence_items)
