from decimal import Decimal

from pydantic import BaseModel, Field, JsonValue

from app.models import UserRole


class BaseAdminRequest(BaseModel):
    """Базовый класс для всех административных запросов"""

    pass


class CourseCreateRequest(BaseAdminRequest):
    """Запрос на создание нового курса"""

    title: str = Field(..., min_length=1, max_length=256, description="Название курса")
    description: str | None = Field(
        None, max_length=10000, description="Описание курса"
    )
    price: Decimal = Field(..., ge=0, decimal_places=2, description="Цена курса")
    is_active: bool = Field(True, description="Активен ли курс")
    img_id: str | None = Field(None, max_length=256, description="ID изображения курса")
    tag_ids: list[str] = Field(default_factory=list, description="Список ID тегов")


class CourseUpdateRequest(BaseAdminRequest):
    """Запрос на обновление существующего курса (частичное обновление)"""

    title: str | None = Field(
        None, min_length=1, max_length=256, description="Новое название курса"
    )
    description: str | None = Field(
        None, max_length=10000, description="Новое описание курса"
    )
    price: Decimal | None = Field(
        None, ge=0, decimal_places=2, description="Новая цена курса"
    )
    is_active: bool | None = Field(None, description="Новый статус активности")
    img_id: str | None = Field(None, max_length=256, description="Новый ID изображения")
    tag_ids: list[str] | None = Field(None, description="Новый список ID тегов")


class ModuleCreateRequest(BaseAdminRequest):
    """Запрос на создание нового модуля"""

    course_id: str = Field(..., description="ID курса")
    title: str = Field(..., min_length=1, max_length=256, description="Название модуля")
    description: str | None = Field(
        None, max_length=10000, description="Описание модуля"
    )
    content_json: JsonValue | None = Field(
        None, description="Контент модуля в формате JSON"
    )
    position: int = Field(..., ge=0, description="Позиция модуля в курсе (начиная с 0)")


class ModuleUpdateRequest(BaseAdminRequest):
    """Запрос на обновление существующего модуля (частичное обновление)"""

    title: str | None = Field(
        None, min_length=1, max_length=256, description="Новое название модуля"
    )
    description: str | None = Field(
        None, max_length=10000, description="Новое описание модуля"
    )
    content_json: JsonValue | None = Field(None, description="Новый контент модуля")
    position: int | None = Field(None, ge=0, description="Новая позиция модуля")


class TestCreateRequest(BaseAdminRequest):
    """Запрос на создание нового теста"""

    module_id: str = Field(..., description="ID модуля")
    title: str = Field(..., min_length=1, max_length=256, description="Название теста")
    description: str | None = Field(
        None, max_length=10000, description="Описание теста"
    )


class TestUpdateRequest(BaseAdminRequest):
    """Запрос на обновление существующего теста (частичное обновление)"""

    title: str | None = Field(
        None, min_length=1, max_length=256, description="Новое название теста"
    )
    description: str | None = Field(
        None, max_length=10000, description="Новое описание теста"
    )


class QuestionCreateRequest(BaseAdminRequest):
    """Запрос на создание нового вопроса"""

    test_id: str = Field(..., description="ID теста")
    question_text: str = Field(..., min_length=1, description="Текст вопроса")


class QuestionUpdateRequest(BaseAdminRequest):
    """Запрос на обновление существующего вопроса (частичное обновление)"""

    question_text: str | None = Field(
        None, min_length=1, description="Новый текст вопроса"
    )


class AnswerOptionCreateRequest(BaseAdminRequest):
    """Запрос на создание нового варианта ответа"""

    question_id: str = Field(..., description="ID вопроса")
    answer_text: str = Field(..., min_length=1, description="Текст варианта ответа")
    is_correct: bool = Field(False, description="Является ли ответ правильным")
    explanation: str | None = Field(
        None, max_length=10000, description="Объяснение ответа"
    )


class AnswerOptionUpdateRequest(BaseAdminRequest):
    """Запрос на обновление существующего варианта ответа (частичное обновление)"""

    answer_text: str | None = Field(
        None, min_length=1, description="Новый текст ответа"
    )
    is_correct: bool | None = Field(None, description="Новый статус правильности")
    explanation: str | None = Field(
        None, max_length=10000, description="Новое объяснение"
    )


class TagCreateRequest(BaseAdminRequest):
    """Запрос на создание нового тега"""

    content: str = Field(
        ..., min_length=1, max_length=256, description="Содержимое тега"
    )


class TagUpdateRequest(BaseAdminRequest):
    """Запрос на обновление существующего тега (частичное обновление)"""

    content: str | None = Field(
        None, min_length=1, max_length=256, description="Новое содержимое тега"
    )


class UserRoleUpdateRequest(BaseAdminRequest):
    """Запрос на изменение роли пользователя"""

    role: UserRole = Field(..., description="Новая роль пользователя (user или admin)")


class ModuleReorderRequest(BaseAdminRequest):
    """Запрос на изменение порядка модулей в курсе"""

    module_positions: dict[str, int] = Field(
        ..., description="Словарь соответствия ID модулей и их новых позиций"
    )
