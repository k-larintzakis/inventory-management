"""
Tests for task API endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def reset_tasks():
    """Clear the in-memory task list and id counter so tests don't leak state."""
    main.tasks.clear()
    main.task_counter = 0
    yield
    main.tasks.clear()
    main.task_counter = 0


def new_task(client, title="Review stock levels", priority="high", due_date="2026-11-10"):
    response = client.post(
        "/api/tasks", json={"title": title, "priority": priority, "dueDate": due_date}
    )
    assert response.status_code == 201
    return response.json()


class TestTasksEndpoints:
    """Test suite for task-related endpoints."""

    def test_get_all_tasks_empty(self, client):
        """Test that no API tasks exist before any are created."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_task(self, client):
        """Test creating a task returns it as pending with a string id."""
        task = new_task(client)
        assert task == {
            "id": "task-1",
            "title": "Review stock levels",
            "priority": "high",
            "dueDate": "2026-11-10",
            "status": "pending",
        }

    def test_get_tasks_newest_first(self, client):
        """Test that created tasks are listed newest first."""
        new_task(client, title="first")
        new_task(client, title="second")

        data = client.get("/api/tasks").json()
        assert [t["title"] for t in data] == ["second", "first"]

    def test_task_ids_not_reused_after_delete(self, client):
        """Test that deleting a task doesn't let the next task reuse its id."""
        new_task(client, title="first")
        second = new_task(client, title="second")
        client.delete(f"/api/tasks/{second['id']}")

        third = new_task(client, title="third")
        assert third["id"] == "task-3"

    def test_toggle_task(self, client):
        """Test that toggling flips status pending -> completed -> pending."""
        task = new_task(client)

        response = client.patch(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        response = client.patch(f"/api/tasks/{task['id']}")
        assert response.json()["status"] == "pending"

    def test_delete_task(self, client):
        """Test deleting a task removes it from the list."""
        task = new_task(client)

        response = client.delete(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        assert client.get("/api/tasks").json() == []

    @pytest.mark.parametrize("method", ["patch", "delete"])
    def test_nonexistent_task(self, client, method):
        """Test toggling or deleting a task that doesn't exist."""
        response = getattr(client, method)("/api/tasks/task-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.parametrize(
        "payload",
        [
            {"title": "", "priority": "high", "dueDate": "2026-11-10"},
            {"title": "x", "priority": "urgent", "dueDate": "2026-11-10"},
            {"title": "x", "priority": "high"},
        ],
        ids=["empty-title", "invalid-priority", "missing-due-date"],
    )
    def test_create_task_validation(self, client, payload):
        """Test that invalid task payloads are rejected."""
        response = client.post("/api/tasks", json=payload)
        assert response.status_code == 422
