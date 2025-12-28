from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, JsonValue

from app.models import UserRole


class BaseAdminResponse(BaseModel):
    """Базовый класс для всех административных ответов"""

    model_config = ConfigDict(from_attributes=True)


class AdminUserResponse(BaseAdminResponse):
    """Административное представление пользователя с дополнительными полями"""

    unique_id: str
    email: EmailStr
    username: str
    role: UserRole
    create_time: datetime
    update_time: datetime


class AdminTagResponse(BaseAdminResponse):
    """Административное представление тега"""

    unique_id: str
    content: str
    create_time: datetime
    update_time: datetime


class AdminAnswerOptionResponse(BaseAdminResponse):
    """Административное представление варианта ответа (с указанием правильности)"""

    unique_id: str
    answer_text: str
    is_correct: bool
    explanation: str | None = None


class AdminQuestionResponse(BaseAdminResponse):
    """Административное представление вопроса со всеми вариантами ответов"""

    unique_id: str
    question_text: str
    answer_options: list[AdminAnswerOptionResponse]


class AdminTestResponse(BaseAdminResponse):
    """Административное представление теста со всеми вопросами"""

    unique_id: str
    module_id: str
    title: str
    description: str | None = None
    questions: list[AdminQuestionResponse]
    create_time: datetime
    update_time: datetime


class AdminModuleResponse(BaseAdminResponse):
    """Административное представление модуля с дополнительными полями"""

    unique_id: str
    course_id: str
    title: str
    description: str | None = None
    content_json: JsonValue | None = None
    position: int
    tests: list[AdminTestResponse] = []
    create_time: datetime
    update_time: datetime


class AdminCourseResponse(BaseAdminResponse):
    """Административное представление курса с полной информацией"""

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
    """Административное представление курса в списке (без полных деталей)"""

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
    """Административное представление модуля в списке (без полных деталей)"""

    unique_id: str
    course_id: str
    title: str
    description: str | None = None
    position: int
    has_test: bool = False
    create_time: datetime
    update_time: datetime


class AdminUserListResponse(BaseAdminResponse):
    """Административное представление пользователя в списке"""

    unique_id: str
    email: EmailStr
    username: str
    role: UserRole
    create_time: datetime
    update_time: datetime


class AdminStatsResponse(BaseAdminResponse):
    """Статистика платформы для администраторов"""

    total_users: int
    total_courses: int
    total_modules: int
    total_tests: int
    total_questions: int
    active_courses: int
    admin_users: int
    regular_users: int


class AdminBulkOperationResponse(BaseAdminResponse):
    """Результат массовой операции"""

    success_count: int
    error_count: int
    errors: list[str] = []


class AdminCourseEnrollmentStats(BaseAdminResponse):
    """Статистика записи на курс"""

    course_id: str
    course_title: str
    total_purchases: int
    total_completions: int
    completion_rate: float
    revenue: Decimal
