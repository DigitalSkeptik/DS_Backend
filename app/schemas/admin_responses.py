from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import UserRole


class BaseAdminResponse(BaseModel):
    """Base class for admin responses"""

    model_config = ConfigDict(from_attributes=True)


class AdminUserResponse(BaseAdminResponse):
    """Admin view of user with additional fields"""

    unique_id: str
    email: EmailStr
    username: str
    role: UserRole
    create_time: datetime
    update_time: datetime


class AdminTagResponse(BaseAdminResponse):
    """Admin view of tag"""

    unique_id: str
    content: str
    create_time: datetime
    update_time: datetime


class AdminAnswerOptionResponse(BaseAdminResponse):
    """Admin view of answer option with correct answer revealed"""

    unique_id: str
    answer_text: str
    is_correct: bool
    explanation: str | None = None


class AdminQuestionResponse(BaseAdminResponse):
    """Admin view of question with all answer options"""

    unique_id: str
    question_text: str
    answer_options: list[AdminAnswerOptionResponse]


class AdminTestResponse(BaseAdminResponse):
    """Admin view of test with all questions"""

    unique_id: str
    module_id: str
    title: str
    description: str | None = None
    questions: list[AdminQuestionResponse]
    create_time: datetime
    update_time: datetime


class AdminModuleResponse(BaseAdminResponse):
    """Admin view of module with additional fields"""

    unique_id: str
    course_id: str
    title: str
    description: str | None = None
    content_json: dict[str, Any] | None = None
    position: int
    tests: list[AdminTestResponse] = []
    create_time: datetime
    update_time: datetime


class AdminCourseResponse(BaseAdminResponse):
    """Admin view of course with additional fields"""

    unique_id: str
    title: str
    description: str | None = None
    price: Decimal
    is_active: bool
    img_id: str | None = None
    modules: list[AdminModuleResponse] = []
    tags: list[AdminTagResponse] = []
    create_time: datetime
    update_time: datetime


class AdminCourseListResponse(BaseAdminResponse):
    """Admin list view of courses without full details"""

    unique_id: str
    title: str
    description: str | None = None
    price: Decimal
    is_active: bool
    img_id: str | None = None
    modules_count: int = 0
    tags: list[AdminTagResponse] = []
    create_time: datetime
    update_time: datetime


class AdminModuleListResponse(BaseAdminResponse):
    """Admin list view of modules without full details"""

    unique_id: str
    course_id: str
    title: str
    description: str | None = None
    position: int
    has_test: bool = False
    create_time: datetime
    update_time: datetime


class AdminUserListResponse(BaseAdminResponse):
    """Admin list view of users"""

    unique_id: str
    email: EmailStr
    username: str
    role: UserRole
    create_time: datetime
    update_time: datetime


class AdminStatsResponse(BaseAdminResponse):
    """Admin statistics"""

    total_users: int
    total_courses: int
    total_modules: int
    total_tests: int
    total_questions: int
    active_courses: int
    admin_users: int
    regular_users: int


class AdminBulkOperationResponse(BaseAdminResponse):
    """Response for bulk operations"""

    success_count: int
    error_count: int
    errors: list[str] = []


class AdminCourseEnrollmentStats(BaseAdminResponse):
    """Course enrollment statistics"""

    course_id: str
    course_title: str
    total_purchases: int
    total_completions: int
    completion_rate: float
    revenue: Decimal
