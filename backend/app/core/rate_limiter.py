import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status

class RateLimiter:
    """
    Simple in-memory rate limiter for zero-cost deployment.
    In production, this would use Redis (Upstash).
    """
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.clients: Dict[str, List[float]] = {}

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip not in self.clients:
            self.clients[client_ip] = []

        # Clean up old requests
        self.clients[client_ip] = [t for t in self.clients[client_ip] if now - t < 60]

        if len(self.clients[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again in a minute."
            )

        self.clients[client_ip].append(now)

rate_limiter = RateLimiter(requests_per_minute=60)
