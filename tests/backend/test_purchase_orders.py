"""
Tests for purchase order API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_purchase_orders():
    """Restore the in-memory purchase order list (loaded from JSON) after each test."""
    original = list(main.purchase_orders)
    yield
    main.purchase_orders[:] = original


def po_payload(backlog_item_id="1", **overrides):
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Acme Industrial",
        "quantity": 350,
        "unit_cost": 4.5,
        "expected_delivery_date": "2026-11-20",
        "notes": "Rush order",
    }
    payload.update(overrides)
    return payload


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client):
        """Test creating a purchase order for a backlog item."""
        response = client.post("/api/purchase-orders", json=po_payload())
        assert response.status_code == 201

        po = response.json()
        assert po["id"].startswith("PO-")
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Industrial"
        assert po["quantity"] == 350
        assert po["status"] == "Pending"
        assert "T" in po["created_date"]
        assert po["notes"] == "Rush order"

    def test_get_purchase_order_by_backlog_item(self, client):
        """Test fetching the purchase order attached to a backlog item."""
        created = client.post("/api/purchase-orders", json=po_payload()).json()

        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 200
        assert response.json() == created

    def test_get_nonexistent_purchase_order(self, client):
        """Test fetching a purchase order for a backlog item without one."""
        response = client.get("/api/purchase-orders/2")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_purchase_order_unknown_backlog_item(self, client):
        """Test that a PO can't be created for a backlog item that doesn't exist."""
        response = client.post("/api/purchase-orders", json=po_payload("nonexistent-999"))
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_duplicate_purchase_order(self, client):
        """Test that a backlog item can only have one purchase order."""
        client.post("/api/purchase-orders", json=po_payload())

        response = client.post("/api/purchase-orders", json=po_payload())
        assert response.status_code == 409

    @pytest.mark.parametrize(
        "overrides",
        [{"quantity": 0}, {"unit_cost": 0}, {"supplier_name": ""}],
        ids=["zero-quantity", "zero-unit-cost", "empty-supplier"],
    )
    def test_create_purchase_order_validation(self, client, overrides):
        """Test that invalid purchase order payloads are rejected."""
        response = client.post("/api/purchase-orders", json=po_payload(**overrides))
        assert response.status_code == 422

    def test_backlog_reports_purchase_order(self, client):
        """Test that the backlog shows which items have a purchase order."""
        po = client.post("/api/purchase-orders", json=po_payload()).json()

        backlog = {item["id"]: item for item in client.get("/api/backlog").json()}
        assert backlog["1"]["has_purchase_order"] is True
        assert backlog["1"]["purchase_order_id"] == po["id"]
        assert backlog["2"]["has_purchase_order"] is False
        assert backlog["2"]["purchase_order_id"] is None
