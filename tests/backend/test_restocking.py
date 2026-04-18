"""
Tests for restocking recommendations API endpoint.
"""
import pytest


class TestRestockingEndpoints:
    """Test suite for the restocking recommendations endpoint."""

    # --- Happy path ---

    def test_get_recommendations_returns_200(self, client):
        """Test that endpoint returns 200 with a valid budget."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        assert response.status_code == 200

    def test_response_structure(self, client):
        """Test that response contains all required top-level fields."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        assert "recommendations" in data
        assert "total_cost" in data
        assert "budget" in data
        assert "remaining_budget" in data
        assert "items_count" in data
        assert "suggestions" in data

        assert isinstance(data["recommendations"], list)
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["total_cost"], (int, float))
        assert isinstance(data["remaining_budget"], (int, float))
        assert isinstance(data["items_count"], int)

    def test_recommendation_item_structure(self, client):
        """Test that each recommendation has all required fields."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        required_fields = [
            "id", "sku", "name", "category", "warehouse",
            "quantity_on_hand", "reorder_point", "recommended_quantity",
            "unit_cost", "subtotal", "priority"
        ]

        for item in data["recommendations"]:
            for field in required_fields:
                assert field in item, f"Missing field: {field}"

    def test_recommendation_field_types(self, client):
        """Test that recommendation fields have correct types and valid ranges."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        for item in data["recommendations"]:
            assert isinstance(item["quantity_on_hand"], int)
            assert isinstance(item["reorder_point"], int)
            assert isinstance(item["recommended_quantity"], int)
            assert isinstance(item["unit_cost"], (int, float))
            assert isinstance(item["subtotal"], (int, float))
            assert item["recommended_quantity"] > 0
            assert item["unit_cost"] > 0
            assert item["subtotal"] > 0

    def test_budget_math_is_consistent(self, client):
        """Test that budget = total_cost + remaining_budget."""
        response = client.get("/api/restocking/recommendations?budget=25000")
        data = response.json()

        assert abs(data["budget"] - (data["total_cost"] + data["remaining_budget"])) < 0.01

    def test_budget_echoed_in_response(self, client):
        """Test that the requested budget is echoed back correctly."""
        response = client.get("/api/restocking/recommendations?budget=30000")
        data = response.json()

        assert data["budget"] == 30000.0

    def test_total_cost_does_not_exceed_budget(self, client):
        """Test that total allocated cost never exceeds the budget."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()

        assert data["total_cost"] <= data["budget"]

    def test_remaining_budget_is_non_negative(self, client):
        """Test that remaining budget is never negative."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        data = response.json()

        assert data["remaining_budget"] >= 0

    def test_items_count_matches_recommendations_length(self, client):
        """Test that items_count matches the actual number of recommendations."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        assert data["items_count"] == len(data["recommendations"])

    def test_subtotal_calculation_per_item(self, client):
        """Test that each item's subtotal equals recommended_quantity * unit_cost."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        for item in data["recommendations"]:
            expected = item["recommended_quantity"] * item["unit_cost"]
            assert abs(item["subtotal"] - expected) < 0.01, (
                f"Subtotal mismatch for {item['sku']}: "
                f"expected {expected}, got {item['subtotal']}"
            )

    def test_priority_values_are_valid(self, client):
        """Test that priority field only contains valid values."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        valid_priorities = {"critical", "high", "medium"}
        for item in data["recommendations"]:
            assert item["priority"] in valid_priorities, (
                f"Invalid priority '{item['priority']}' for {item['sku']}"
            )

    def test_demand_trend_values_are_valid(self, client):
        """Test that demand_trend is null or a valid trend string."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        data = response.json()

        valid_trends = {"increasing", "decreasing", "stable", None}
        for item in data["recommendations"]:
            assert item.get("demand_trend") in valid_trends, (
                f"Invalid trend '{item.get('demand_trend')}' for {item['sku']}"
            )

    # --- Filter tests ---

    def test_filter_by_warehouse(self, client):
        """Test that warehouse filter restricts recommendations to that warehouse."""
        response = client.get(
            "/api/restocking/recommendations?budget=50000&warehouse=Tokyo"
        )
        assert response.status_code == 200
        data = response.json()

        for item in data["recommendations"]:
            assert item["warehouse"] == "Tokyo"

        for item in data["suggestions"]:
            assert item["warehouse"] == "Tokyo"

    def test_filter_by_category(self, client):
        """Test that category filter restricts recommendations to that category."""
        response = client.get(
            "/api/restocking/recommendations?budget=50000&category=Sensors"
        )
        assert response.status_code == 200
        data = response.json()

        for item in data["recommendations"]:
            assert item["category"].lower() == "sensors"

    def test_filter_by_warehouse_and_category(self, client):
        """Test combined warehouse and category filters."""
        response = client.get(
            "/api/restocking/recommendations?budget=100000&warehouse=London&category=Sensors"
        )
        assert response.status_code == 200
        data = response.json()

        for item in data["recommendations"]:
            assert item["warehouse"] == "London"
            assert item["category"].lower() == "sensors"

    def test_filter_returns_fewer_results_than_unfiltered(self, client):
        """Test that filtering by warehouse returns fewer or equal items than no filter."""
        unfiltered = client.get("/api/restocking/recommendations?budget=100000").json()
        filtered = client.get(
            "/api/restocking/recommendations?budget=100000&warehouse=Tokyo"
        ).json()

        total_unfiltered = len(unfiltered["recommendations"]) + len(unfiltered["suggestions"])
        total_filtered = len(filtered["recommendations"]) + len(filtered["suggestions"])

        assert total_filtered <= total_unfiltered

    # --- Budget edge cases ---

    def test_very_small_budget_returns_empty_or_partial(self, client):
        """Test that a very small budget returns no or few recommendations."""
        response = client.get("/api/restocking/recommendations?budget=1")
        assert response.status_code == 200

        data = response.json()
        assert data["total_cost"] <= 1.0
        assert data["remaining_budget"] >= 0

    def test_large_budget_returns_all_eligible_items(self, client):
        """Test that a very large budget allocates to all eligible items."""
        response = client.get("/api/restocking/recommendations?budget=10000000")
        assert response.status_code == 200

        data = response.json()
        assert len(data["recommendations"]) > 0
        # With a huge budget, suggestions should be empty (everything is affordable)
        assert len(data["suggestions"]) == 0

    # --- Suggestions structure ---

    def test_suggestion_item_structure(self, client):
        """Test that suggestions have all required fields."""
        # Use a modest budget that is likely to leave some items unaffordable
        response = client.get("/api/restocking/recommendations?budget=100")
        data = response.json()

        required_fields = [
            "sku", "name", "category", "warehouse",
            "priority", "min_budget_needed", "full_restock_cost"
        ]

        for s in data["suggestions"]:
            for field in required_fields:
                assert field in s, f"Suggestion missing field: {field}"

    def test_suggestion_min_budget_exceeds_remaining(self, client):
        """Test that each suggestion's min_budget_needed exceeds remaining budget."""
        response = client.get("/api/restocking/recommendations?budget=500")
        data = response.json()

        remaining = data["remaining_budget"]
        for s in data["suggestions"]:
            assert s["min_budget_needed"] > remaining, (
                f"Suggestion {s['sku']} should not be affordable with remaining ${remaining}"
            )

    def test_full_restock_cost_gte_min_budget_needed(self, client):
        """Test that full_restock_cost >= min_budget_needed for each suggestion."""
        response = client.get("/api/restocking/recommendations?budget=500")
        data = response.json()

        for s in data["suggestions"]:
            assert s["full_restock_cost"] >= s["min_budget_needed"], (
                f"full_restock_cost should be >= min_budget_needed for {s['sku']}"
            )

    # --- Validation / error cases ---

    def test_missing_budget_returns_422(self, client):
        """Test that omitting budget returns a 422 validation error."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_invalid_budget_string_returns_422(self, client):
        """Test that a non-numeric budget returns a 422 validation error."""
        response = client.get("/api/restocking/recommendations?budget=notanumber")
        assert response.status_code == 422
