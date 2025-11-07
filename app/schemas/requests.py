from pydantic import BaseModel, EmailStr, Field


class BaseRequest(BaseModel):
    # may define additional fields or config shared across requests
    pass


class RefreshTokenRequest(BaseRequest):
    refresh_token: str


class UserUpdatePasswordRequest(BaseRequest):
    password: str


class UserCreateRequest(BaseRequest):
    email: EmailStr
    password: str
    username: str


class UserLoginRequest(BaseRequest):
    email: EmailStr
    password: str


class TestAnswerRequest(BaseRequest):
    """Single answer in test submission"""

    question_id: str = Field(..., description="UUID of the question")
    selected_option_id: str = Field(..., description="UUID of selected answer option")


class TestSubmissionRequest(BaseRequest):
    """Complete test submission with all answers"""

    answers: list[TestAnswerRequest] = Field(..., min_length=1)
