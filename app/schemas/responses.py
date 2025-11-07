from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseResponse):
    token_type: str = "Bearer"
    access_token: str
    expires_at: int
    refresh_token: str
    refresh_token_expires_at: int


class UserResponse(BaseResponse):
    unique_id: str
    email: EmailStr
    username: str


class AnswerOptionResponse(BaseResponse):
    """Answer option for a question (when retrieving test)"""

    option_id: str
    answer_text: str


class QuestionResponse(BaseResponse):
    """Question with answer options (when retrieving test)"""

    question_id: str
    question_text: str
    answer_options: list[AnswerOptionResponse]


class TestResponse(BaseResponse):
    """Complete test for taking"""

    test_id: str
    module_id: str
    title: str
    description: str | None = None
    questions: list[QuestionResponse]


class CorrectAnswerResponse(BaseResponse):
    """Correct answer with explanation"""

    option_id: str
    answer_text: str
    explanation: str | None = None


class QuestionResultResponse(BaseResponse):
    """Result for a single question"""

    question_id: str
    question_text: str
    selected_option_id: str
    is_correct: bool
    correct_option: CorrectAnswerResponse


class TestSubmissionResponse(BaseResponse):
    """Complete test submission result"""

    test_id: str
    score_percentage: float
    passed: bool
    passing_threshold: int = 70
    total_questions: int
    correct_answers: int
    module_completed: bool
    results: list[QuestionResultResponse]


class ModuleTestStatusResponse(BaseResponse):
    """Module test completion status"""

    module_id: str
    has_test: bool
    completed: bool
    completed_at: datetime | None = None
