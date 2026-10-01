import logging
import math
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.tracking import LocationTracking
from app.models.user import User

logger = logging.getLogger(__name__)

class LocationService:
    async def update_location(
        self,
        db: AsyncSession,
        user_id: int,
        lat: float,
        lon: float,
        floor: int = 0,
        building: str = "Main"
    ):
        """
        Record the user's current indoor/outdoor location with PostGIS geometry.
        """
        result = await db.execute(
            select(LocationTracking).filter(LocationTracking.user_id == user_id)
        )
        tracking = result.scalars().first()

        if not tracking:
            tracking = LocationTracking(user_id=user_id)
            db.add(tracking)

        tracking.latitude = lat
        tracking.longitude = lon
        tracking.location = f"POINT({lon} {lat})"
        tracking.floor = floor
        tracking.building = building
        tracking.created_at = datetime.utcnow()
        tracking.is_active = True

        await db.commit()
        return tracking

    async def get_nearest_staff_by_coords(
        self,
        db: AsyncSession,
        lat: float,
        lon: float,
        max_distance_meters: float = 100.0,
        limit: int = 3
    ):
        """
        Find nearest available staff within max_distance_meters using PostGIS ST_DWithin / ST_Distance with Haversine fallback.
        """
        try:
            from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_SetSRID, ST_MakePoint, ST_Geography

            point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
            geog_point = func.ST_Geography(point)
            geog_loc = func.ST_Geography(LocationTracking.location)

            query = (
                select(User, LocationTracking, func.ST_Distance(geog_loc, geog_point).label("dist_meters"))
                .join(LocationTracking, User.id == LocationTracking.user_id)
                .filter(
                    User.role.in_(["doctor", "nurse", "staff", "admin"]),
                    LocationTracking.is_active == True,
                    LocationTracking.location.is_not(None),
                    func.ST_DWithin(geog_loc, geog_point, max_distance_meters)
                )
                .order_by("dist_meters")
                .limit(limit)
            )

            result = await db.execute(query)
            candidates = result.all()
            if candidates:
                staff_list = []
                for user, loc, dist in candidates:
                    distance = float(dist) if dist is not None else 0.0
                    eta_seconds = max(30, int(distance / 1.4))
                    staff_list.append({
                        "staff_id": user.id,
                        "name": getattr(user, 'first_name', user.email.split('@')[0]) or user.email,
                        "role": user.role,
                        "distance_meters": round(distance, 1),
                        "estimated_arrival_minutes": math.ceil(eta_seconds / 60)
                    })
                return staff_list
        except Exception as exc:
            logger.warning(f"PostGIS spatial query failed/unsupported, using Haversine calculation: {exc}")

        result = await db.execute(
            select(User, LocationTracking)
            .join(LocationTracking, User.id == LocationTracking.user_id)
            .filter(
                User.role.in_(["doctor", "nurse", "staff", "admin"]),
                LocationTracking.is_active == True
            )
        )
        candidates = result.all()

        staff_list = []
        for user, loc in candidates:
            if loc.latitude is not None and loc.longitude is not None:
                dlat = math.radians(loc.latitude - lat)
                dlon = math.radians(loc.longitude - lon)
                a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(loc.latitude)) * math.sin(dlon / 2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                distance = 6371000 * c

                if distance <= max_distance_meters:
                    eta_seconds = max(30, int(distance / 1.4))
                    staff_list.append({
                        "staff_id": user.id,
                        "name": getattr(user, 'first_name', user.email.split('@')[0]) or user.email,
                        "role": user.role,
                        "distance_meters": round(distance, 1),
                        "estimated_arrival_minutes": math.ceil(eta_seconds / 60)
                    })

        staff_list.sort(key=lambda x: x["distance_meters"])
        return staff_list[:limit]

location_service = LocationService()
