"""Master agent: aggregate results and produce a final recommendation."""

from __future__ import annotations

import logging
from typing import Dict, List

from utils.llm import analyze_with_llm, get_llm
from utils.state import RFPState

logger = logging.getLogger(__name__)


def _compose_recommendation(state: RFPState, llm=None) -> str:
    """Create a human-readable recommendation using LLM."""
    comparison = state.get("comparison_report", {})
    ranked: List[Dict] = comparison.get("ranked_products", [])
    risk_level = state.get("risk_report", {}).get("risk_level", "UNKNOWN")
    pricing_summary = state.get("pricing_summary", {})
    
    if not ranked:
        return "No suitable products found. Please refine requirements."

    top = ranked[0]
    
    # Use LLM to generate comprehensive recommendation
    if llm is None:
        from utils.llm import get_llm
        llm = get_llm()
    
    recommendation_context = {
        "top_product": f"SKU: {top.get('sku')}, Name: {top.get('product_name')}, Price: ${top.get('estimated_price')}, Score: {top.get('composite_score')}",
        "risk_level": risk_level,
        "pricing_summary": f"Total: ${pricing_summary.get('total_estimated')}, Average: ${pricing_summary.get('average_estimated')}",
        "comparison_explanation": comparison.get("llm_explanation", "N/A"),
        "requirements": str(state.get("extracted_requirements", {})),
    }
    
    recommendation_prompt = f"""Generate a comprehensive procurement recommendation based on the following analysis:

Top Product: {recommendation_context['top_product']}
Risk Level: {recommendation_context['risk_level']}
Pricing: {recommendation_context['pricing_summary']}
Comparison Reasoning: {recommendation_context['comparison_explanation']}
Requirements: {recommendation_context['requirements']}

Provide a clear, executive-level recommendation that includes:
1. Recommended SKU and product name
2. Estimated price
3. Key technical specifications that match
4. Risk assessment
5. Rationale for the recommendation
6. Any important considerations or caveats

Format as a professional recommendation suitable for procurement decision-makers."""

    try:
        recommendation = analyze_with_llm(recommendation_prompt, context=None, llm=llm)
        if recommendation:
            return recommendation
    except Exception as e:
        logger.warning(f"[MASTER AGENT] LLM recommendation generation failed: {str(e)}, using fallback")
    
    # Fallback to simple recommendation
    lines = [
        f"Recommended SKU: {top.get('sku')} - {top.get('product_name')}",
        f"Estimated price: {top.get('estimated_price')} USD",
        f"Composite score: {top.get('composite_score')}",
        f"Risk level: {risk_level}",
        "Rationale: best technical match with competitive pricing and acceptable risk.",
    ]
    return "\n".join(lines)


def master_agent(state: RFPState, redis_client=None) -> RFPState:
    """Aggregate pipeline outputs into a final recommendation."""
    rfp_id = state.get("rfp_id", "rfp")
    logger.info(f"[MASTER AGENT] Starting final aggregation for RFP: {rfp_id}")
    logger.info(f"[MASTER AGENT] Received state from RISK & COMPLIANCE AGENT. Status: {state.get('status', 'UNKNOWN')}")
    
    logger.info("[MASTER AGENT] Aggregating results from all agents:")
    logger.info(f"[MASTER AGENT]   Technical matches: {len(state.get('matched_products', []))}")
    logger.info(f"[MASTER AGENT]   Pricing items: {len(state.get('pricing_summary', {}).get('items', []))}")
    logger.info(f"[MASTER AGENT]   Ranked products: {len(state.get('comparison_report', {}).get('ranked_products', []))}")
    logger.info(f"[MASTER AGENT]   Risk level: {state.get('risk_report', {}).get('risk_level', 'UNKNOWN')}")
    
    logger.info("[MASTER AGENT] Using Gemini Flash 2.5 to generate comprehensive recommendation...")
    recommendation = _compose_recommendation(state)
    logger.info(f"[MASTER AGENT] Generated final recommendation:")
    logger.info(f"[MASTER AGENT] {recommendation}")
    
    updated: RFPState = {
        **state,
        "final_recommendation": recommendation,
        "status": "COMPLETED",
    }
    
    logger.info(f"[MASTER AGENT] Pipeline COMPLETED for RFP: {rfp_id}")
    return updated


