from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models import UserRole


class BaseAdminRequest(BaseModel):
    """Base class for admin requests"""

    pass


class CourseCreateRequest(BaseAdminRequest):
    """Request to create a new course"""

    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None, max_length=10000)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    is_active: bool = True
    img_id: str | None = Field(None, max_length=256)
    tag_ids: list[str] = Field(default_factory=list)


class CourseUpdateRequest(BaseAdminRequest):
    """Request to update an existing course"""

    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=10000)
    price: Decimal | None = Field(None, ge=0, decimal_places=2)
    is_active: bool | None = None
    img_id: str | None = Field(None, max_length=256)
    tag_ids: list[str] | None = None


class ModuleCreateRequest(BaseAdminRequest):
    """Request to create a new module"""

    course_id: str
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None, max_length=10000)
    content_json: dict[str, Any] | None = None
    position: int = Field(..., ge=0)


class ModuleUpdateRequest(BaseAdminRequest):
    """Request to update an existing module"""

    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=10000)
    content_json: dict[str, Any] | None = None
    position: int | None = Field(None, ge=0)


class TestCreateRequest(BaseAdminRequest):
    """Request to create a new test"""

    module_id: str
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(None, max_length=10000)


class TestUpdateRequest(BaseAdminRequest):
    """Request to update an existing test"""

    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, max_length=10000)


class QuestionCreateRequest(BaseAdminRequest):
    """Request to create a new question"""

    test_id: str
    question_text: str = Field(..., min_length=1)


class QuestionUpdateRequest(BaseAdminRequest):
    """Request to update an existing question"""

    question_text: str | None = Field(None, min_length=1)


class AnswerOptionCreateRequest(BaseAdminRequest):
    """Request to create a new answer option"""

    question_id: str
    answer_text: str = Field(..., min_length=1)
    is_correct: bool = False
    explanation: str | None = Field(None, max_length=10000)


class AnswerOptionUpdateRequest(BaseAdminRequest):
    """Request to update an existing answer option"""

    answer_text: str | None = Field(None, min_length=1)
    is_correct: bool | None = None
    explanation: str | None = Field(None, max_length=10000)


class TagCreateRequest(BaseAdminRequest):
    """Request to create a new tag"""

    content: str = Field(..., min_length=1, max_length=256)


class TagUpdateRequest(BaseAdminRequest):
    """Request to update an existing tag"""

    content: str | None = Field(None, min_length=1, max_length=256)


class UserRoleUpdateRequest(BaseAdminRequest):
    """Request to update a user's role"""

    role: UserRole = Field(..., description="New role for the user")


class ModuleReorderRequest(BaseAdminRequest):
    """Request to reorder modules in a course"""

    module_positions: dict[str, int] = Field(
        ..., description="Dictionary mapping module IDs to their new positions"
    )
