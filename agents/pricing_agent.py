"""Pricing agent: compute estimates and highlight cost drivers."""

from __future__ import annotations

import logging
from typing import Dict, List

from utils.llm import analyze_with_llm, get_llm
from utils.redis_store import cache_json
from utils.state import RFPState

logger = logging.getLogger(__name__)


def _estimate_pricing(matches: List[Dict]) -> Dict:
    """Generate a simple pricing breakdown."""
    items = []
    total = 0.0
    for product in matches:
        base_price = float(product.get("base_price") or 0.0)
        # Apply heuristic multipliers based on conductor and armor
        multiplier = 1.0
        if (product.get("conductor_material") or "").lower() == "copper":
            multiplier += 0.12
        if (product.get("armor") or "").lower() not in ("none", ""):
            multiplier += 0.05
        estimate = round(base_price * multiplier, 2)
        items.append(
            {
                "sku": product.get("sku"),
                "product_name": product.get("product_name"),
                "base_price": base_price,
                "estimated_price": estimate,
                "drivers": {
                    "conductor_material": product.get("conductor_material"),
                    "armor": product.get("armor"),
                },
            }
        )
        total += estimate
    return {
        "items": items,
        "total_estimated": round(total, 2),
        "average_estimated": round(total / len(items), 2) if items else 0.0,
        "currency": "USD",
    }


def pricing_agent(state: RFPState, redis_client=None) -> RFPState:
    """Estimate pricing for matched products."""
    rfp_id = state.get("rfp_id", "rfp")
    logger.info(f"[PRICING AGENT] Starting processing for RFP: {rfp_id}")
    logger.info(f"[PRICING AGENT] Received state from TECHNICAL AGENT. Status: {state.get('status', 'UNKNOWN')}")
    
    matches = state.get("matched_products") or []
    logger.info(f"[PRICING AGENT] Processing pricing for {len(matches)} matched products")
    
    summary = _estimate_pricing(matches)
    logger.info(f"[PRICING AGENT] Generated pricing summary:")
    logger.info(f"[PRICING AGENT]   Total estimated: ${summary.get('total_estimated')}")
    logger.info(f"[PRICING AGENT]   Average estimated: ${summary.get('average_estimated')}")
    logger.info(f"[PRICING AGENT]   Items: {len(summary.get('items', []))}")
    
    # Use LLM for pricing analysis and anomaly detection
    if matches:
        logger.info("[PRICING AGENT] Using Gemini Flash 2.5 for pricing analysis...")
        pricing_context = {
            "products": str([{"sku": m.get("sku"), "base_price": m.get("base_price"), "estimated": summary.get("items", [{}])[i].get("estimated_price")} for i, m in enumerate(matches[:5])]),
            "total_estimated": str(summary.get("total_estimated")),
            "average_estimated": str(summary.get("average_estimated")),
        }
        analysis = analyze_with_llm(
            "Analyze these product prices. Identify any anomalies, cost drivers, or pricing concerns. Provide a brief analysis.",
            context=pricing_context
        )
        summary["llm_analysis"] = analysis
        logger.info(f"[PRICING AGENT] LLM response received (pricing analysis, {len(analysis)} chars)")

    cache_key = f"rfp:{rfp_id}:pricing"
    cache_json(redis_client, cache_key, summary)
    logger.info(f"[PRICING AGENT] Cached pricing summary to Redis: {cache_key}")

    updated: RFPState = {
        **state,
        "pricing_summary": summary,
        "status": "PRICING_READY",
    }
    
    logger.info(f"[PRICING AGENT] Completed. Status: PRICING_READY. Passing to COMPARISON AGENT")
    return updated


