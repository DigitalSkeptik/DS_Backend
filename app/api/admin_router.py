from fastapi import APIRouter

from app.api.endpoints.v1 import (
    admin,
    admin_modules,
    admin_questions,
    admin_tags,
    admin_tests,
    admin_users,
)
from app.api.endpoints.v2 import (
    admin as admin_v2,
)
from app.api.endpoints.v2 import (
    admin_modules as admin_modules_v2,
)
from app.api.endpoints.v2 import (
    admin_questions as admin_questions_v2,
)
from app.api.endpoints.v2 import (
    admin_tags as admin_tags_v2,
)
from app.api.endpoints.v2 import (
    admin_tests as admin_tests_v2,
)
from app.api.endpoints.v2 import (
    admin_users as admin_users_v2,
)

router_v1, router_v2 = APIRouter(), APIRouter()
router_v1.include_router(admin.router, prefix="/courses", tags=["admin-courses"])
router_v1.include_router(admin_modules.router, tags=["admin-modules"])
router_v1.include_router(admin_tests.router, tags=["admin-tests"])
router_v1.include_router(admin_questions.router, tags=["admin-questions"])
router_v1.include_router(admin_tags.router, prefix="/tags", tags=["admin-tags"])
router_v1.include_router(admin_users.router, prefix="/users", tags=["admin-users"])

router_v2.include_router(admin_v2.router, prefix="/courses", tags=["admin-courses"])
router_v2.include_router(admin_modules_v2.router, tags=["admin-modules"])
router_v2.include_router(admin_tests_v2.router, tags=["admin-tests"])
router_v2.include_router(admin_questions_v2.router, tags=["admin-questions"])
router_v2.include_router(admin_tags_v2.router, prefix="/tags", tags=["admin-tags"])
router_v2.include_router(admin_users_v2.router, prefix="/users", tags=["admin-users"])
