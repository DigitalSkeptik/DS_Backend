from fastapi import APIRouter

from app.api import admin_router, api_messages
from app.api.endpoints import auth, tests, users

auth_router = APIRouter()
auth_router.include_router(auth.router, prefix="/auth", tags=["auth"])

api_router = APIRouter(
    responses={
        401: {
            "description": "No `Authorization` access token header, token is invalid or user removed",
            "content": {
                "application/json": {
                    "examples": {
                        "not authenticated": {
                            "summary": "No authorization token header",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid token": {
                            "summary": "Token validation failed, decode failed, it may be expired or malformed",
                            "value": {"detail": "Token invalid: {detailed error msg}"},
                        },
                        "removed user": {
                            "summary": api_messages.JWT_ERROR_USER_REMOVED,
                            "value": {"detail": api_messages.JWT_ERROR_USER_REMOVED},
                        },
                    }
                }
            },
        },
        403: {
            "description": "Admin access required",
            "content": {
                "application/json": {"example": {"detail": "Admin access required"}}
            },
        },
    }
)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tests.router, prefix="/tests", tags=["tests"])
api_router.include_router(admin_router.router, prefix="/admin", tags=["admin"])
