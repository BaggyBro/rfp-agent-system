"""Shared LangGraph state definition for the RFP pipeline."""

from typing import Any, Dict, List, TypedDict


class RFPState(TypedDict, total=False):
    """Typed state carried through the LangGraph pipeline."""

    rfp_id: str
    raw_text: str
    chunks: List[str]
    abstract: str
    extracted_requirements: Dict[str, Any]
    matched_products: List[Dict[str, Any]]
    pricing_summary: Dict[str, Any]
    comparison_report: Dict[str, Any]
    risk_report: Dict[str, Any]
    final_recommendation: str
    status: str


