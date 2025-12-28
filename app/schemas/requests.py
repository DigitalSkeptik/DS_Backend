from pydantic import BaseModel, EmailStr, Field


class BaseRequest(BaseModel):
    """Базовый класс для всех запросов"""

    pass


class RefreshTokenRequest(BaseRequest):
    """Запрос на обновление access токена"""

    refresh_token: str = Field(
        ..., description="Refresh токен для получения нового access токена"
    )


class UserUpdatePasswordRequest(BaseRequest):
    """Запрос на смену пароля пользователя"""

    password: str = Field(
        ...,
        description="Новый пароль (мин. 8 символов, должен содержать буквы, цифры и спецсимволы)",
    )


class UserCreateRequest(BaseRequest):
    """Запрос на регистрацию нового пользователя"""

    email: EmailStr = Field(..., description="Email адрес пользователя")
    password: str = Field(
        ...,
        description="Пароль (мин. 8 символов, должен содержать буквы, цифры и спецсимволы)",
    )
    username: str = Field(..., description="Имя пользователя")


class UserLoginRequest(BaseRequest):
    """Запрос на вход в систему"""

    email: EmailStr = Field(..., description="Email адрес пользователя")
    password: str = Field(..., description="Пароль пользователя")


class TestAnswerRequest(BaseRequest):
    """Ответ на один вопрос теста"""

    question_id: str = Field(..., description="UUID вопроса")
    selected_option_id: str = Field(..., description="UUID выбранного варианта ответа")


class TestSubmissionRequest(BaseRequest):
    """Отправка теста со всеми ответами"""

    answers: list[TestAnswerRequest] = Field(
        ..., min_length=1, description="Список ответов на все вопросы теста"
    )
