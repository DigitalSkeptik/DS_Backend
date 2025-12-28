from fastapi import APIRouter

from app.api import admin_router, api_messages, user_side_router

v1_api_router = APIRouter(
    responses={
        401: {
            "description": "No `Authorization` access token or API key (for internal requests) header, token is invalid or user removed",
            "content": {
                "application/json": {
                    "examples": {
                        "not authenticated": {
                            "summary": "No authorization token header",
                            "value": {"detail": "Not authenticated"},
                        },
                        "no api key": {
                            "summary": 'No API key for internal requests is found in headers ({"WWW-Authenticate": "ApiKey"})',
                            "value": {
                                "detail": "API key required for internal endpoints"
                            },
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
v1_api_router.include_router(user_side_router.router_v1)
v1_api_router.include_router(admin_router.router_v1, prefix="/admin")


v2_api_router = APIRouter(
    responses={
        401: {
            "description": "No `Authorization` access token or API key (for internal requests) header, token is invalid or user removed",
            "content": {
                "application/json": {
                    "examples": {
                        "not authenticated": {
                            "summary": "No authorization token header",
                            "value": {"detail": "Not authenticated"},
                        },
                        "no api key": {
                            "summary": 'No API key for internal requests is found in headers ({"WWW-Authenticate": "ApiKey"})',
                            "value": {
                                "detail": "API key required for internal endpoints"
                            },
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
v2_api_router.include_router(user_side_router.router_v2)
v2_api_router.include_router(admin_router.router_v2, prefix="/admin")
