from agents import technical_agent
from main import build_graph


def test_pipeline_with_stubbed_catalog(monkeypatch):
    """Run the pipeline with a stubbed product catalog to avoid DB dependency."""

    def fake_query_products(filters, limit=10):
        return [
            {
                "sku": "CAB_0001",
                "product_name": "3-core 1.1kV XLPE Copper",
                "voltage": "1.1kV",
                "insulation": "XLPE",
                "core_count": 3,
                "cross_section_mm2": 10.0,
                "armor": "Steel",
                "standard": "IS 1554",
                "base_price": 120.0,
                "conductor_material": "Copper",
            }
        ]

    monkeypatch.setattr(technical_agent, "query_products", fake_query_products)

    app = build_graph(redis_client=None)
    final_state = app.invoke(
        {
            "rfp_id": "stubbed",
            "raw_text": "We need 3-core copper cables, XLPE insulated, per IS 1554, rated 1.1kV.",
            "status": "INGESTING",
        }
    )

    assert final_state["status"] == "COMPLETED"
    assert final_state["comparison_report"]["ranked_products"]
