"""Entry point for the LangGraph-powered RFP pipeline."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from functools import partial
from typing import Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.graph import END, StateGraph

from agents.comparison_agent import comparison_agent
from agents.master_agent import master_agent
from agents.pricing_agent import pricing_agent
from agents.risk_compliance_agent import risk_compliance_agent
from agents.sales_agent import extract_text, sales_agent
from agents.technical_agent import technical_agent
from utils.redis_store import get_redis_client
from utils.state import RFPState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="RFP Processing Pipeline",
    description="AI-powered RFP automation prototype",
)

# CORS for Next.js frontend on http://localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_graph(redis_client=None):
    """Construct the LangGraph pipeline."""
    logger.info("[PIPELINE] Building LangGraph workflow")
    graph = StateGraph(RFPState)

    graph.add_node("sales", partial(sales_agent, redis_client=redis_client))
    graph.add_node("technical", partial(technical_agent, redis_client=redis_client))
    graph.add_node("pricing", partial(pricing_agent, redis_client=redis_client))
    graph.add_node("comparison", partial(comparison_agent, redis_client=redis_client))
    graph.add_node("risk", partial(risk_compliance_agent, redis_client=redis_client))
    graph.add_node("master", partial(master_agent, redis_client=redis_client))

    graph.set_entry_point("sales")
    graph.add_edge("sales", "technical")
    graph.add_edge("technical", "pricing")
    graph.add_edge("pricing", "comparison")
    graph.add_edge("comparison", "risk")
    graph.add_edge("risk", "master")
    graph.add_edge("master", END)

    logger.info("[PIPELINE] Graph compiled with 6 agents: sales -> technical -> pricing -> comparison -> risk -> master")
    return graph.compile()


def run_pipeline(raw_text: str, rfp_id: str = "rfp-demo") -> Dict:
    """Run the end-to-end RFP flow and return the final state."""
    logger.info(f"[PIPELINE] Starting RFP processing pipeline for: {rfp_id}")
    logger.info(f"[PIPELINE] Input text length: {len(raw_text)} characters")
    
    redis_client = get_redis_client()
    if redis_client:
        logger.info("[PIPELINE] Redis client connected successfully")
    else:
        logger.warning("[PIPELINE] Redis client not available, continuing without caching")
    
    app = build_graph(redis_client=redis_client)
    initial_state: RFPState = {
        "rfp_id": rfp_id,
        "raw_text": raw_text,
        "status": "INGESTING",
    }
    
    logger.info("[PIPELINE] Invoking LangGraph workflow...")
    final_state = app.invoke(initial_state)
    logger.info(f"[PIPELINE] Pipeline completed with status: {final_state.get('status', 'UNKNOWN')}")
    
    return final_state


def _load_text(path: str) -> str:
    """Load text from a file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_pdf(path: str) -> bytes:
    """Load PDF file as bytes."""
    with open(path, "rb") as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="AI-powered RFP processing pipeline")
    parser.add_argument("--rfp-path", type=str, help="Path to a text or PDF RFP file")
    parser.add_argument("--rfp-id", type=str, default="rfp-demo", help="RFP identifier for tracking")
    args = parser.parse_args()

    if not args.rfp_path:
        print("No --rfp-path supplied. Provide a text or PDF file to process.")
        sys.exit(1)

    if not os.path.exists(args.rfp_path):
        print(f"File not found: {args.rfp_path}")
        sys.exit(1)

    # Detect file type and load accordingly
    if args.rfp_path.lower().endswith(".pdf"):
        pdf_bytes = _load_pdf(args.rfp_path)
        # Extract text from PDF for processing
        from agents.sales_agent import extract_text
        raw_text = extract_text(pdf_bytes)
    else:
        raw_text = _load_text(args.rfp_path)
    
    final_state = run_pipeline(raw_text, rfp_id=args.rfp_id)

    print("\n" + "=" * 60)
    print("FINAL RECOMMENDATION")
    print("=" * 60)
    print(final_state.get("final_recommendation", "No recommendation available"))
    
    print("\n" + "=" * 60)
    print("COMPARISON REPORT")
    print("=" * 60)
    comparison = final_state.get("comparison_report", {})
    if isinstance(comparison, dict):
        ranked = comparison.get("ranked_products", [])
        if ranked:
            print(f"\nTop {min(3, len(ranked))} ranked products:")
            for idx, product in enumerate(ranked[:3], 1):
                print(f"\n{idx}. {product.get('sku')} - {product.get('product_name')}")
                print(f"   Score: {product.get('composite_score')}, Price: ${product.get('estimated_price')}")
        print(f"\nMethodology: {comparison.get('methodology', 'N/A')}")
    else:
        print(comparison)
    
    print("\n" + "=" * 60)
    print("RISK REPORT")
    print("=" * 60)
    risk = final_state.get("risk_report", {})
    if isinstance(risk, dict):
        print(f"Risk Level: {risk.get('risk_level', 'UNKNOWN')}")
        missing = risk.get("missing_fields", [])
        if missing:
            print(f"Missing fields: {', '.join(missing)}")
        findings = risk.get("compliance_findings", [])
        if findings:
            compliant_count = sum(1 for f in findings if f.get("compliant"))
            print(f"Compliance: {compliant_count}/{len(findings)} products compliant")
    else:
        print(risk)
    
    print("\n" + "=" * 60)


# FastAPI endpoints
@app.post("/rfp-upload/")
async def rfp_upload_endpoint(
    file: UploadFile = File(...),
    rfp_id: str = "rfp-api",
):
    """
    Upload and process an RFP PDF file through the full pipeline.
    
    User Flow:
    1. User uploads PDF file via POST /rfp-upload/
    2. Sales Agent: Extracts text, chunks document, generates abstract
    3. Technical Agent: Extracts requirements, queries PostgreSQL catalog, matches products
    4. Pricing Agent: Estimates pricing for matched products
    5. Comparison Agent: Ranks products by composite score
    6. Risk & Compliance Agent: Validates standards, assigns risk level
    7. Master Agent: Aggregates all results into final recommendation
    8. Returns JSON response with complete analysis
    """
    logger.info(f"[API] Received RFP upload request: {file.filename}, RFP ID: {rfp_id}")
    logger.info(f"[API] Content type: {file.content_type}")
    
    try:
        # Read file content
        if file.content_type == "application/pdf":
            logger.info("[API] Processing PDF file")
            pdf_bytes = await file.read()
            logger.info(f"[API] PDF file size: {len(pdf_bytes)} bytes")
            raw_text = extract_text(pdf_bytes)
            logger.info(f"[API] Extracted {len(raw_text)} characters from PDF")
        elif file.content_type in ["text/plain", "text/markdown"]:
            logger.info("[API] Processing text file")
            raw_text = (await file.read()).decode("utf-8")
            logger.info(f"[API] Text file length: {len(raw_text)} characters")
        else:
            logger.error(f"[API] Unsupported file type: {file.content_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Use PDF or text files."
            )
        
        # Run pipeline
        logger.info(f"[API] Starting pipeline execution for RFP: {rfp_id}")
        final_state = run_pipeline(raw_text, rfp_id=rfp_id)
        logger.info(f"[API] Pipeline completed successfully for RFP: {rfp_id}")
        
        response_data = {
            "rfp_id": rfp_id,
            "status": final_state.get("status", "UNKNOWN"),
            "final_recommendation": final_state.get("final_recommendation"),
            "comparison_report": final_state.get("comparison_report"),
            "risk_report": final_state.get("risk_report"),
            "extracted_requirements": final_state.get("extracted_requirements"),
            "matched_products_count": len(final_state.get("matched_products", [])),
        }
        
        logger.info(f"[API] Returning response for RFP: {rfp_id}")
        return JSONResponse(content=response_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Processing failed for RFP {rfp_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/process-rfp/")
async def process_rfp_endpoint(
    file: UploadFile = File(...),
    rfp_id: str = "rfp-api",
):
    """Process an RFP file (PDF or text) through the full pipeline. (Alias for /rfp-upload/)"""
    return await rfp_upload_endpoint(file, rfp_id)


@app.post("/process-rfp-text/")
async def process_rfp_text_endpoint(
    text: str,
    rfp_id: str = "rfp-api",
):
    """Process RFP text directly through the full pipeline."""
    try:
        final_state = run_pipeline(text, rfp_id=rfp_id)
        return JSONResponse(content={
            "rfp_id": rfp_id,
            "status": final_state.get("status", "UNKNOWN"),
            "final_recommendation": final_state.get("final_recommendation"),
            "comparison_report": final_state.get("comparison_report"),
            "risk_report": final_state.get("risk_report"),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "RFP Processing Pipeline"}


if __name__ == "__main__":
    main()
