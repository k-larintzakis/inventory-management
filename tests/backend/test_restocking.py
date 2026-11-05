"""
Tests for restocking order API endpoints.
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def reset_restocking_orders():
    """Clear the module-level in-memory order list so tests don't leak state."""
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


def line(sku, quantity, name="ignored", unit_cost=0.01, lead_time_days=1):
    """Build a request line item. Price and lead time are deliberately wrong to
    prove the server re-prices from its own forecast data."""
    return {
        "sku": sku,
        "name": name,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "lead_time_days": lead_time_days,
    }


class TestDemandForecastPricing:
    """The demand forecast now carries the fields restocking depends on."""

    def test_demand_forecast_pricing_fields(self, client):
        """Test that every forecast has a positive unit cost and lead time."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        for forecast in response.json():
            assert isinstance(forecast["unit_cost"], (int, float))
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["unit_cost"] > 0
            assert forecast["lead_time_days"] > 0


class TestRestockingOrderEndpoints:
    """Test suite for restocking order endpoints."""

    def test_get_restocking_orders_empty(self, client):
        """Test that no orders exist before any are submitted."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restocking_order(self, client):
        """Test creating an order computes total, lead time, and ETA."""
        # WDG-001: 24.99, 7 days. FLT-405: 8.25, 5 days.
        payload = {"items": [line("WDG-001", 150), line("FLT-405", 150)], "budget": 10000}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"] == "RST-0001"
        assert order["status"] == "Submitted"
        assert abs(order["total_cost"] - (150 * 24.99 + 150 * 8.25)) < 0.01
        assert order["lead_time_days"] == 7

        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert expected - submitted == timedelta(days=7)

    def test_create_restocking_order_uses_server_pricing(self, client):
        """Test that client-supplied price, name, and lead time are ignored."""
        payload = {"items": [line("WDG-001", 10)], "budget": 1000}
        order = client.post("/api/restocking-orders", json=payload).json()

        item = order["items"][0]
        assert item["unit_cost"] == 24.99
        assert item["lead_time_days"] == 7
        assert item["name"] == "Industrial Widget Type A"

    def test_created_order_appears_in_list(self, client):
        """Test that submitted orders are listed newest first."""
        client.post("/api/restocking-orders", json={"items": [line("GSK-203", 10)], "budget": 1000})
        client.post("/api/restocking-orders", json={"items": [line("PSU-501", 10)], "budget": 1000})

        data = client.get("/api/restocking-orders").json()
        assert [o["order_number"] for o in data] == ["RST-0002", "RST-0001"]

    def test_create_restocking_order_unknown_sku(self, client):
        """Test that an unknown SKU is rejected."""
        payload = {"items": [line("NOPE-999", 1)], "budget": 1000}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    def test_create_restocking_order_over_budget(self, client):
        """Test that an order costing more than the budget is rejected and not stored."""
        # 10 x 445.00 = 4450, well over a 100 budget even though the client claims 0.01 each.
        payload = {"items": [line("MTR-304", 10)], "budget": 100}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()
        assert client.get("/api/restocking-orders").json() == []

    def test_create_restocking_order_duplicate_sku(self, client):
        """Test that the same SKU twice in one order is rejected."""
        payload = {"items": [line("WDG-001", 1), line("WDG-001", 2)], "budget": 1000}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()

    def test_create_restocking_order_negative_budget(self, client):
        """Test that a negative budget fails validation."""
        payload = {"items": [line("WDG-001", 1)], "budget": -1}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 422

    def test_create_restocking_order_empty_items(self, client):
        """Test that an order with no items fails validation."""
        response = client.post("/api/restocking-orders", json={"items": [], "budget": 1000})
        assert response.status_code == 422

    def test_create_restocking_order_zero_quantity(self, client):
        """Test that a zero quantity fails validation."""
        payload = {"items": [line("WDG-001", 0)], "budget": 1000}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 422
