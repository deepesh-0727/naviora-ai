"""Role and permission dependencies shared by API routes."""

from collections.abc import Callable
from functools import wraps
from inspect import Parameter, iscoroutinefunction, signature
from typing import Any

from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.api.deps import get_current_active_user

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "patient": frozenset({"view_own_profile", "manage_own_profile", "manage_own_appointments", "trigger_emergency"}),
    "doctor": frozenset({"view_patient", "manage_queue", "manage_prescriptions", "manage_labs"}),
    "nurse": frozenset({"view_patient", "record_vitals", "manage_medications", "manage_handover"}),
    "front_desk": frozenset({"manage_appointments", "register_walk_in", "manage_payments"}),
    "pharmacy": frozenset({"view_prescriptions", "dispense_medications"}),
    "facilities": frozenset({"manage_beds", "manage_equipment", "manage_maintenance"}),
    "emergency": frozenset({"view_emergency", "manage_emergency"}),
    "admin": frozenset({"manage_staff", "manage_departments", "view_audit", "view_patient"}),
    "super_admin": frozenset({"manage_staff", "manage_departments", "view_audit", "manage_system", "view_patient"}),
    # Legacy staff accounts use the generic role while their accounts are migrated.
    "staff": frozenset({"view_patient", "manage_queue", "manage_appointments"}),
}


def _denied(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_role(*roles: str) -> Callable[..., Any]:
    """FastAPI dependency suitable for ``Depends(require_role(...))``."""
    allowed = frozenset(roles)
    if not allowed:
        raise ValueError("require_role needs at least one role")

    def role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed:
            raise _denied(
                f"Role '{current_user.role}' is not authorized; required role: "
                f"{', '.join(sorted(allowed))}."
            )
        return current_user

    return role_dependency


def require_permission(permission: str) -> Callable[..., Any]:
    """FastAPI dependency that checks the authenticated user's role permissions."""
    if not permission:
        raise ValueError("permission must not be empty")

    def permission_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        permissions = ROLE_PERMISSIONS.get(current_user.role, frozenset())
        if permission not in permissions:
            raise _denied(f"Role '{current_user.role}' lacks permission '{permission}'.")
        return current_user

    return permission_dependency


def role_guard(roles: tuple[str, ...]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator form for routes; FastAPI still resolves the injected user."""
    dependency = require_role(*roles)

    def decorate(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        original_signature = signature(endpoint)
        injected_parameter = Parameter(
            "_rbac_user",
            kind=Parameter.KEYWORD_ONLY,
            default=Depends(dependency),
            annotation=User,
        )
        guarded_signature = original_signature.replace(
            parameters=[*original_signature.parameters.values(), injected_parameter]
        )

        if iscoroutinefunction(endpoint):
            @wraps(endpoint)
            async def guarded(*args: Any, **kwargs: Any) -> Any:
                kwargs.pop("_rbac_user", None)
                return await endpoint(*args, **kwargs)
        else:
            @wraps(endpoint)
            async def guarded(*args: Any, **kwargs: Any) -> Any:
                kwargs.pop("_rbac_user", None)
                return endpoint(*args, **kwargs)

        guarded.__signature__ = guarded_signature
        return guarded

    return decorate
