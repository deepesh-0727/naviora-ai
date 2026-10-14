from fastapi import HTTPException


class RoutePlanner:
    """Indoor route lookup is available once routes are stored in the database."""

    def find_path(self, start: str, end: str, needs_accessible: bool = False):
        raise HTTPException(
            status_code=501,
            detail="Indoor routes are not configured for this hospital.",
        )


route_planner = RoutePlanner()
