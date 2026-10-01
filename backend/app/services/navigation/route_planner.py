import logging
import heapq
from typing import List, Dict, Tuple, Optional, Any
from app.core.exceptions import NavioraError

logger = logging.getLogger(__name__)

class RoutePlanner:
    """
    Enterprise Indoor Navigation Engine.
    Uses a weighted directed graph to calculate optimal paths across multiple hospital floors.
    Accounts for accessibility (wheelchairs) and transport mode (stairs vs elevator).
    """
    def __init__(self):
        # Full Hospital Topology
        # weight = (time_in_seconds, accessibility_factor)
        self.graph = {
            "G_ENTRANCE": {
                "G_RECEPTION": (30, True),
                "G_PHARMACY": (45, True)
            },
            "G_RECEPTION": {
                "G_ENTRANCE": (30, True),
                "G_ELEVATOR_A": (60, True),
                "G_STAIRS_1": (40, False),
                "G_CANTEEN": (90, True)
            },
            "G_ELEVATOR_A": {
                "G_RECEPTION": (60, True),
                "F1_CARDIOLOGY": (120, True), # Includes elevator wait time
                "F2_ORTHOPEDICS": (150, True)
            },
            "F1_CARDIOLOGY": {
                "G_ELEVATOR_A": (120, True),
                "F1_ICU": (45, True),
                "F1_NURSE_STATION": (20, True)
            },
            "F1_ICU": {
                "F1_CARDIOLOGY": (45, True),
                "F1_NURSE_STATION": (30, True)
            },
            "G_PHARMACY": {
                "G_ENTRANCE": (45, True),
                "G_BLOOD_BANK": (120, True)
            }
        }

    def find_path(self, start: str, end: str, needs_accessible: bool = False) -> Dict[str, Any]:
        """
        Dijkstra's Algorithm optimized for clinical environments.
        """
        if start not in self.graph or end not in self.graph:
            logger.error(f"Navigation failure: Invalid nodes {start} -> {end}")
            return {"error": "Invalid location nodes", "path": [], "time": 0}

        queue = [(0, start, [])]
        seen = set()
        distances = {start: 0}

        while queue:
            (cost, current_node, path) = heapq.heappop(queue)

            if current_node in seen:
                continue

            seen.add(current_node)
            path = path + [current_node]

            if current_node == end:
                return {
                    "path": path,
                    "estimated_seconds": cost,
                    "human_readable": self._generate_instructions(path),
                    "accessible": True
                }

            for neighbor, (weight, is_accessible) in self.graph.get(current_node, {}).items():
                if needs_accessible and not is_accessible:
                    continue

                new_cost = cost + weight
                if new_cost < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_cost
                    heapq.heappush(queue, (new_cost, neighbor, path))

        return {"error": "No viable path found", "path": [], "time": 0}

    def _generate_instructions(self, path: List[str]) -> List[str]:
        instructions = []
        for i in range(len(path) - 1):
            curr, next_node = path[i], path[i+1]
            if "ELEVATOR" in next_node:
                instructions.append(f"Proceed to {next_node.replace('_', ' ')} and wait for the lift.")
            elif "F1" in next_node and "G" in curr:
                instructions.append("Take the lift or stairs to the First Floor.")
            else:
                instructions.append(f"Walk towards {next_node.replace('_', ' ')}.")
        instructions.append("You have arrived at your destination.")
        return instructions

route_planner = RoutePlanner()
