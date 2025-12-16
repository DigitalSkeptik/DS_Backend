from fastapi import APIRouter

from app.api.endpoints.v1 import (
    auth,
    courses,
    modules,
    tests,
    users,
)
from app.api.endpoints.v2 import (
    auth as auth_v2,
)
from app.api.endpoints.v2 import (
    courses as courses_v2,
)
from app.api.endpoints.v2 import (
    modules as modules_v2,
)
from app.api.endpoints.v2 import (
    tests as tests_v2,
)
from app.api.endpoints.v2 import (
    users as users_v2,
)

router_v1, router_v2 = APIRouter(), APIRouter()

router_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
router_v1.include_router(users.router, prefix="/users", tags=["users"])
router_v1.include_router(tests.router, prefix="/tests", tags=["tests"])
router_v1.include_router(courses.router, prefix="/courses", tags=["courses"])
router_v1.include_router(modules.router, prefix="/modules", tags=["modules"])

router_v2.include_router(auth_v2.router, prefix="/auth", tags=["auth"])
router_v2.include_router(users_v2.router, prefix="/users", tags=["users"])
router_v2.include_router(tests_v2.router, prefix="/tests", tags=["tests"])
router_v2.include_router(courses_v2.router, prefix="/courses", tags=["courses"])
router_v2.include_router(modules_v2.router, prefix="/modules", tags=["modules"])
