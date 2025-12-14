from fastapi import APIRouter

from app.api.endpoints import (
    admin,
    admin_modules,
    admin_questions,
    admin_tags,
    admin_tests,
    admin_users,
)

router = APIRouter()

# Course management
router.include_router(admin.router, prefix="/courses", tags=["admin-courses"])

# Module management
router.include_router(admin_modules.router, tags=["admin-modules"])

# Test management
router.include_router(admin_tests.router, tags=["admin-tests"])

# Question and answer management
router.include_router(admin_questions.router, tags=["admin-questions"])

# Tag management
router.include_router(admin_tags.router, prefix="/tags", tags=["admin-tags"])

# User management
router.include_router(admin_users.router, prefix="/users", tags=["admin-users"])
