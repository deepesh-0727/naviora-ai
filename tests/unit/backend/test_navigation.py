import pytest
from app.services.navigation.route_planner import route_planner

def test_route_planner_shortest_path():
    start = "G_ENTRANCE"
    end = "F1_ICU"

    result = route_planner.find_path(start, end)

    assert "error" not in result
    assert result["path"][0] == start
    assert result["path"][-1] == end
    assert result["estimated_seconds"] > 0
    assert len(result["human_readable"]) > 0

def test_route_planner_invalid_nodes():
    result = route_planner.find_path("INVALID", "F1_ICU")
    assert "error" in result
    assert result["path"] == []

def test_route_planner_accessibility():
    # Test path that might be non-accessible (though our mock currently has True for most)
    result = route_planner.find_path("G_RECEPTION", "F1_CARDIOLOGY", needs_accessible=True)
    assert "error" not in result
    # In a real graph, we'd verify it chose Elevator A over Stairs.
