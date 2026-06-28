"""Risk & compliance agent: validate standards and assign risk level."""

from __future__ import annotations

import logging
from typing import Dict, List

from utils.llm import analyze_with_llm, get_llm
from utils.redis_store import cache_json
from utils.state import RFPState

logger = logging.getLogger(__name__)


def _compute_risk(requirements: Dict[str, str], candidates: List[Dict]) -> Dict:
    """Assess compliance risk based on standards and missing attributes."""
    required_standard = requirements.get("standard", "").lower()
    missing_fields = [k for k in ["voltage", "insulation", "core_count"] if k not in requirements]

    compliance_findings = []
    non_compliant = 0
    for product in candidates:
        product_standard = str(product.get("standard", "")).lower()
        compliant = required_standard in product_standard if required_standard else True
        if not compliant:
            non_compliant += 1
        compliance_findings.append(
            {
                "sku": product.get("sku"),
                "standard": product.get("standard"),
                "compliant": compliant,
            }
        )

    risk_level = "LOW"
    if missing_fields or non_compliant > len(candidates) / 2:
        risk_level = "MEDIUM"
    if non_compliant == len(candidates) and len(candidates) > 0:
        risk_level = "HIGH"

    return {
        "risk_level": risk_level,
        "missing_fields": missing_fields,
        "compliance_findings": compliance_findings,
    }


def risk_compliance_agent(state: RFPState, redis_client=None) -> RFPState:
    """Perform compliance checks and tag risk level."""
    rfp_id = state.get("rfp_id", "rfp")
    logger.info(f"[RISK & COMPLIANCE AGENT] Starting processing for RFP: {rfp_id}")
    logger.info(f"[RISK & COMPLIANCE AGENT] Received state from COMPARISON AGENT. Status: {state.get('status', 'UNKNOWN')}")
    
    requirements = state.get("extracted_requirements") or {}
    candidates = state.get("matched_products") or []
    logger.info(f"[RISK & COMPLIANCE AGENT] Assessing risk for {len(candidates)} candidates")
    logger.info(f"[RISK & COMPLIANCE AGENT] Requirements: {requirements}")
    
    report = _compute_risk(requirements, candidates)
    logger.info(f"[RISK & COMPLIANCE AGENT] Risk assessment complete:")
    logger.info(f"[RISK & COMPLIANCE AGENT]   Risk Level: {report.get('risk_level')}")
    logger.info(f"[RISK & COMPLIANCE AGENT]   Missing fields: {report.get('missing_fields')}")
    
    compliant_count = sum(1 for f in report.get("compliance_findings", []) if f.get("compliant"))
    logger.info(f"[RISK & COMPLIANCE AGENT]   Compliance: {compliant_count}/{len(candidates)} products compliant")
    
    # Use LLM for intelligent risk assessment
    if candidates:
        logger.info("[RISK & COMPLIANCE AGENT] Using Gemini Flash 2.5 for risk analysis...")
        risk_context = {
            "requirements": str(requirements),
            "risk_level": report.get("risk_level"),
            "missing_fields": str(report.get("missing_fields")),
            "compliance_rate": f"{compliant_count}/{len(candidates)}",
            "sample_products": str([{"sku": c.get("sku"), "standard": c.get("standard"), "compliant": report.get("compliance_findings", [{}])[i].get("compliant")} for i, c in enumerate(candidates[:3])]),
        }
        risk_analysis = analyze_with_llm(
            "Analyze the compliance and risk level. Identify potential issues, missing certifications, or ambiguities. Provide recommendations.",
            context=risk_context
        )
        report["llm_risk_analysis"] = risk_analysis
        logger.info(f"[RISK & COMPLIANCE AGENT] LLM response received (risk analysis, {len(risk_analysis)} chars)")

    cache_key = f"rfp:{rfp_id}:risk"
    cache_json(redis_client, cache_key, report)
    logger.info(f"[RISK & COMPLIANCE AGENT] Cached risk report to Redis: {cache_key}")

    updated: RFPState = {
        **state,
        "risk_report": report,
        "status": "RISK_COMPLIANCE_READY",
    }
    
    logger.info(f"[RISK & COMPLIANCE AGENT] Completed. Status: RISK_COMPLIANCE_READY. Passing to MASTER AGENT")
    return updated


