from main import build_graph


def test_graph_compiles():
    """Ensure the LangGraph pipeline compiles without Redis/DB."""
    app = build_graph(redis_client=None)
    result = app.invoke(
        {
            "rfp_id": "test",
            "raw_text": "Section 1 Cable requirements: 3-core copper XLPE per IS 1554 standard at 1.1kV.",
            "status": "INGESTING",
        }
    )
    assert result["status"] == "COMPLETED"
    assert "final_recommendation" in result
