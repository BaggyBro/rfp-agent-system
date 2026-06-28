"""Comparison agent: rank candidate products by technical fit and cost."""

from __future__ import annotations

import logging
from typing import Dict, List

from utils.llm import analyze_with_llm, get_llm
from utils.redis_store import cache_json
from utils.state import RFPState

logger = logging.getLogger(__name__)


def _rank_products(matches: List[Dict], pricing_summary: Dict) -> List[Dict]:
    """Combine match score and pricing to create a ranked list."""
    price_lookup = {item["sku"]: item["estimated_price"] for item in pricing_summary.get("items", [])}
    ranked = []
    for product in matches:
        price = price_lookup.get(product.get("sku"), product.get("base_price", 0.0))
        match_score = float(product.get("match_score", 0.0))
        # Lower price is better; combine with match score
        composite_score = round(match_score * 0.7 + (1 / (price + 1e-6)) * 0.3, 4)
        ranked.append(
            {
                **product,
                "estimated_price": price,
                "composite_score": composite_score,
            }
        )
    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    return ranked


def comparison_agent(state: RFPState, redis_client=None) -> RFPState:
    """Create a side-by-side comparison of candidates."""
    rfp_id = state.get("rfp_id", "rfp")
    logger.info(f"[COMPARISON AGENT] Starting processing for RFP: {rfp_id}")
    logger.info(f"[COMPARISON AGENT] Received state from PRICING AGENT. Status: {state.get('status', 'UNKNOWN')}")
    
    matches = state.get("matched_products") or []
    pricing_summary = state.get("pricing_summary") or {}
    logger.info(f"[COMPARISON AGENT] Comparing {len(matches)} products with pricing data")
    
    ranked = _rank_products(matches, pricing_summary)
    logger.info(f"[COMPARISON AGENT] Ranked {len(ranked)} products")

    if ranked:
        top_3 = ranked[:3]
        logger.info(f"[COMPARISON AGENT] Top 3 products:")
        for idx, product in enumerate(top_3, 1):
            logger.info(f"[COMPARISON AGENT]   {idx}. {product.get('sku')} - Score: {product.get('composite_score')}, Price: ${product.get('estimated_price')}")
        
        # Use LLM for explainable ranking
        logger.info("[COMPARISON AGENT] Using Gemini Flash 2.5 for ranking explanation...")
        comparison_context = {
            "top_products": str([{"sku": p.get("sku"), "name": p.get("product_name"), "score": p.get("composite_score"), "price": p.get("estimated_price"), "match_score": p.get("match_score")} for p in top_3]),
            "methodology": "Composite score = 70% technical match + 30% inverse price",
        }
        explanation = analyze_with_llm(
            "Explain why these products are ranked in this order. Provide reasoning for the top recommendation considering technical fit, pricing, and value.",
            context=comparison_context
        )
        logger.info(f"[COMPARISON AGENT] LLM response received (ranking explanation, {len(explanation)} chars)")
    else:
        explanation = "No products to compare."

    report = {
        "ranked_products": ranked,
        "methodology": "Composite score = 70% technical match + 30% inverse price",
        "llm_explanation": explanation,
    }

    cache_key = f"rfp:{rfp_id}:comparison"
    cache_json(redis_client, cache_key, report)
    logger.info(f"[COMPARISON AGENT] Cached comparison report to Redis: {cache_key}")

    updated: RFPState = {
        **state,
        "comparison_report": report,
        "status": "COMPARISON_READY",
    }
    
    logger.info(f"[COMPARISON AGENT] Completed. Status: COMPARISON_READY. Passing to RISK & COMPLIANCE AGENT")
    return updated


