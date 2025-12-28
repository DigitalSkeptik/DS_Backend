from datetime import datetime
from decimal import Decimal
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.pagination import PaginatedResponse

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Базовый класс для всех ответов API"""

    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseResponse):
    """Ответ с токенами доступа после входа или регистрации"""

    token_type: str = "Bearer"
    access_token: str
    expires_at: int
    refresh_token: str
    refresh_token_expires_at: int


class UserResponse(BaseResponse):
    """Информация о пользователе"""

    unique_id: str
    email: EmailStr
    username: str


class AnswerOptionResponse(BaseResponse):
    """Вариант ответа на вопрос (при получении теста, без указания правильности)"""

    option_id: str
    answer_text: str


class QuestionResponse(BaseResponse):
    """Вопрос с вариантами ответов (при получении теста)"""

    question_id: str
    question_text: str
    answer_options: list[AnswerOptionResponse]


class TestResponse(BaseResponse):
    """Полный тест для прохождения"""

    test_id: str
    module_id: str
    title: str
    description: str | None = None
    questions: list[QuestionResponse]


class CorrectAnswerResponse(BaseResponse):
    """Правильный ответ с объяснением"""

    option_id: str
    answer_text: str
    explanation: str | None = None


class QuestionResultResponse(BaseResponse):
    """Результат проверки одного вопроса"""

    question_id: str
    question_text: str
    selected_option_id: str
    is_correct: bool
    correct_option: CorrectAnswerResponse


class TestSubmissionResponse(BaseResponse):
    """Результат отправки теста"""

    test_id: str
    score_percentage: float
    passed: bool
    passing_threshold: int = 70
    total_questions: int
    correct_answers: int
    module_completed: bool
    results: list[QuestionResultResponse]


class ModuleTestStatusResponse(BaseResponse):
    """Статус прохождения теста модуля"""

    module_id: str
    has_test: bool
    completed: bool
    completed_at: datetime | None = None


class TagResponse(BaseResponse):
    """Тег курса"""

    unique_id: str
    content: str


class ModuleResponse(BaseResponse):
    """Базовая информация о модуле"""

    unique_id: str
    course_id: str
    title: str
    description: str | None = None
    position: int


class CourseListResponse(BaseResponse):
    """Курс в списке (v1 - без персонализации)"""

    unique_id: str
    title: str
    description: str | None = None
    price: Decimal
    img_id: str | None = None
    modules_count: int
    tags: list[TagResponse] = []
    is_active: bool


class CourseDetailResponse(BaseResponse):
    """Детальная информация о курсе (v1 - без персонализации)"""

    unique_id: str
    title: str
    description: str | None = None
    price: Decimal
    img_id: str | None = None
    modules: list[ModuleResponse] = []
    tags: list[TagResponse] = []
    is_active: bool


class CourseListResponseV2(CourseListResponse):
    """Курс в списке (v2 - с персонализацией)"""

    user_discount: int | None = None
    final_price: Decimal
    is_purchased: bool


class CourseDetailResponseV2(CourseDetailResponse):
    """Детальная информация о курсе (v2 - с персонализацией и прогрессом)"""

    user_discount: int | None = None
    final_price: Decimal
    is_purchased: bool
    completion_percentage: float | None = None


class ModuleDetailResponse(BaseResponse):
    """Детальная информация о модуле с контентом (для купивших курс)"""

    unique_id: str
    course_id: str
    title: str
    description: str | None = None
    content_json: dict | None = None  # type: ignore[type-arg]
    position: int
    is_completed: bool = False
    has_test: bool = False
    test_completed: bool = False


# Paginated response types
PaginatedCourseListResponse = PaginatedResponse[CourseListResponse]
PaginatedCourseListResponseV2 = PaginatedResponse[CourseListResponseV2]
PaginatedModuleResponse = PaginatedResponse[ModuleResponse]
