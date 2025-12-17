"""Technical agent: extract requirements and match catalog products."""

from __future__ import annotations

import logging
import re
from typing import Dict, List

from utils.db import query_products
from utils.llm import extract_structured_data, get_llm
from utils.redis_store import cache_json
from utils.state import RFPState

logger = logging.getLogger(__name__)


def _extract_requirements(text: str) -> Dict[str, str]:
    """Lightweight requirement extraction using regex heuristics."""
    requirements: Dict[str, str] = {}
    voltage_match = re.search(r"(\d+(?:\.\d+)?\s?kV)", text, re.IGNORECASE)
    if voltage_match:
        requirements["voltage"] = voltage_match.group(1)

    insulation_match = re.search(r"\b(PVC|XLPE|EPR)\b", text, re.IGNORECASE)
    if insulation_match:
        requirements["insulation"] = insulation_match.group(1).upper()

    core_match = re.search(r"(\d+)\s*-?\s*core", text, re.IGNORECASE)
    if core_match:
        requirements["core_count"] = core_match.group(1)

    standard_match = re.search(r"(IS\s?\d+|IEC\s?\d+|BS\s?\d+)", text, re.IGNORECASE)
    if standard_match:
        requirements["standard"] = standard_match.group(1).upper()

    conductor_match = re.search(r"\b(Copper|Aluminum)\b", text, re.IGNORECASE)
    if conductor_match:
        requirements["conductor_material"] = conductor_match.group(1).capitalize()

    return requirements


def _score_product(product: Dict, requirements: Dict[str, str]) -> float:
    """Assign a simple match score based on satisfied attributes."""
    score = 0.0
    for key in ["voltage", "insulation", "standard", "conductor_material"]:
        if key in requirements:
            req_val = str(requirements[key]).lower().strip()
            prod_val = str(product.get(key, "")).lower().strip()
            if req_val and prod_val and req_val in prod_val or prod_val in req_val:
                score += 1.0
    
    # Special handling for core_count (numeric comparison)
    if "core_count" in requirements:
        try:
            req_count = int(requirements["core_count"])
            prod_count = int(product.get("core_count", 0))
            if req_count == prod_count:
                score += 1.0
        except (ValueError, TypeError):
            pass
    
    return score


def technical_agent(state: RFPState, redis_client=None) -> RFPState:
    """
    Extract requirements and pull candidate SKUs from the product catalog.
    Uses Gemini Flash 2.5 for intelligent requirement extraction.
    """
    rfp_id = state.get("rfp_id", "rfp")
    logger.info(f"[TECHNICAL AGENT] Starting processing for RFP: {rfp_id}")
    logger.info(f"[TECHNICAL AGENT] Received state from SALES AGENT. Status: {state.get('status', 'UNKNOWN')}")
    logger.info(f"[TECHNICAL AGENT] Received {len(state.get('chunks', []))} chunks")
    
    text_source = state.get("raw_text") or " ".join(state.get("chunks", []))
    logger.info(f"[TECHNICAL AGENT] Extracting requirements from text ({len(text_source)} chars)")
    
    # Use LLM for intelligent requirement extraction
    logger.info("[TECHNICAL AGENT] Using Gemini Flash 2.5 for requirement extraction...")
    schema_desc = """Extract these technical specifications:
- voltage: Cable voltage rating (e.g., "0.6/1kV", "1.1/2kV")
- insulation: Insulation material (PVC, XLPE, or EPR)
- core_count: Number of cores (integer)
- standard: Applicable standard (e.g., "IS 1554", "IEC 60502", "BS 5467")
- conductor_material: Conductor material (Copper or Aluminum)
- cross_section_mm2: Cross-sectional area in mm² (if specified)
- armor: Armor type (Steel, Aluminum, None, or Copper)"""
    
    llm_requirements = extract_structured_data(text_source, schema_desc)
    
    # Fallback to regex extraction for any missing fields
    regex_requirements = _extract_requirements(text_source)
    
    # Merge: prefer LLM results, fallback to regex
    requirements = {**regex_requirements, **{k: v for k, v in llm_requirements.items() if v is not None}}
    
    logger.info(f"[TECHNICAL AGENT] Extracted requirements (LLM + regex): {requirements}")
    
    logger.info(f"[TECHNICAL AGENT] Querying PostgreSQL catalog with filters: {requirements}")
    catalog_results = query_products(requirements, limit=10)
    logger.info(f"[TECHNICAL AGENT] Found {len(catalog_results)} products from catalog")

    matches: List[Dict] = []
    for product in catalog_results:
        score = _score_product(product, requirements)
        reason = (
            f"Matches voltage={product.get('voltage')} insulation={product.get('insulation')} "
            f"core_count={product.get('core_count')}"
        )
        matches.append(
            {
                **product,
                "match_score": round(score, 2),
                "reason": reason,
            }
        )
        logger.debug(f"[TECHNICAL AGENT] Scored product {product.get('sku')}: {round(score, 2)}")

    logger.info(f"[TECHNICAL AGENT] Matched {len(matches)} products with scores")
    if matches:
        top_match = max(matches, key=lambda x: x.get("match_score", 0))
        logger.info(f"[TECHNICAL AGENT] Top match: {top_match.get('sku')} (score: {top_match.get('match_score')})")

    cache_key = f"rfp:{rfp_id}:technical"
    cache_json(redis_client, cache_key, {"requirements": requirements, "matches": matches})
    logger.info(f"[TECHNICAL AGENT] Cached technical results to Redis: {cache_key}")

    updated: RFPState = {
        **state,
        "extracted_requirements": requirements,
        "matched_products": matches,
        "status": "TECHNICAL_READY",
    }
    
    logger.info(f"[TECHNICAL AGENT] Completed. Status: TECHNICAL_READY. Passing {len(matches)} products to PRICING AGENT")
    return updated


