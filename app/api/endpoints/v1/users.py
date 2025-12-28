from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages, deps
from app.core.security.password import get_password_hash, is_password_too_simple
from app.models import RefreshToken, User
from app.schemas.requests import UserUpdatePasswordRequest
from app.schemas.responses import UserResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получить текущего пользователя",
    response_description="Информация о текущем пользователе",
)
async def read_current_user(
    current_user: User = Depends(deps.get_current_user),
) -> User:
    """
    Получить информацию о текущем авторизованном пользователе.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен

    ## Возвращаемые данные

    - `unique_id` - уникальный идентификатор пользователя (UUID)
    - `email` - email адрес пользователя
    - `username` - имя пользователя

    **Примечание**: Пароль и другие чувствительные данные не возвращаются.

    ## Примеры использования

    ```bash
    # Получить информацию о себе
    GET /api/v2/users/me
    Authorization: Bearer <token>
    ```

    ## Использование

    Этот эндпоинт полезен для:
    - Отображения профиля пользователя
    - Проверки авторизации
    - Получения ID пользователя для других запросов
    - Отображения имени в UI

    ## Ошибки

    - **401 Unauthorized**: Не авторизован или токен недействителен
    """
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить текущего пользователя",
    response_description="Успешное удаление (без тела ответа)",
)
async def delete_current_user(
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> None:
    """
    Удалить учетную запись текущего пользователя.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен

    ## Описание

    Полностью удаляет учетную запись пользователя и все связанные данные:
    - Профиль пользователя
    - Все refresh токены
    - Связанные данные (через каскадное удаление)

    ## Важно

    - **Операция необратима**: Восстановление невозможно
    - **Каскадное удаление**: Удаляются все связанные записи
    - **Немедленный эффект**: Токены становятся недействительными

    ## Что удаляется

    - Учетная запись пользователя
    - Все refresh токены
    - История покупок курсов
    - Прогресс прохождения курсов
    - Завершенные модули
    - Персональные скидки

    ## Примеры использования

    ```bash
    # Удалить свою учетную запись
    DELETE /api/v2/users/me
    Authorization: Bearer <token>
    ```

    ## Ответ

    При успехе возвращается статус **204 No Content** без тела ответа.

    ## Рекомендации

    - Показывайте предупреждение перед удалением
    - Требуйте подтверждение от пользователя
    - Рассмотрите возможность "мягкого" удаления (деактивация)

    ## Ошибки

    - **401 Unauthorized**: Не авторизован или токен недействителен
    """
    await session.execute(
        delete(RefreshToken).where(RefreshToken.user_id == current_user.unique_id)
    )
    await session.execute(delete(User).where(User.unique_id == current_user.unique_id))
    await session.commit()


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Сменить пароль",
    response_description="Успешная смена пароля (без тела ответа)",
)
async def reset_current_user_password(
    user_update_password: UserUpdatePasswordRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Сменить пароль текущего пользователя.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен

    ## Требования к новому паролю

    Новый пароль должен соответствовать требованиям безопасности:
    - Минимум 8 символов
    - Содержать заглавные и строчные буквы
    - Содержать цифры
    - Содержать специальные символы
    - Не должен быть слишком простым

    ## Входные данные

    - `password` - новый пароль (обязательно)

    ## Процесс смены пароля

    1. Проверка требований безопасности
    2. Хеширование нового пароля (bcrypt, 12 раундов)
    3. Обновление пароля в базе данных
    4. Сохранение изменений

    **Примечание**: Существующие токены остаются действительными. Для полной безопасности
    рекомендуется также выйти из всех сессий (удалить refresh токены).

    ## Примеры использования

    ```bash
    # Сменить пароль
    POST /api/v2/users/reset-password
    Authorization: Bearer <token>
    Content-Type: application/json

    {
      "password": "NewSecurePass123!@#"
    }
    ```

    ## Ответ

    При успехе возвращается статус **204 No Content** без тела ответа.

    ## Безопасность

    - Старый пароль не требуется (пользователь уже авторизован)
    - Новый пароль хешируется перед сохранением
    - Пароль никогда не хранится в открытом виде
    - Используется bcrypt с 12 раундами

    ## Рекомендации

    После смены пароля рекомендуется:
    - Выйти из всех других сессий
    - Уведомить пользователя по email
    - Залогиниться заново с новым паролем

    ## Ошибки

    - **401 Unauthorized**: Не авторизован или токен недействителен
    - **422 Unprocessable Entity**: Пароль не соответствует требованиям безопасности
      - Детальное сообщение указывает конкретную проблему
    """
    pass_check_result = is_password_too_simple(user_update_password.password)

    if pass_check_result:
        detail = (
            pass_check_result[1]
            if isinstance(pass_check_result, tuple)
            else api_messages.PASSWORD_INVALID
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    current_user.pass_hash = get_password_hash(user_update_password.password)
    session.add(current_user)
    await session.commit()
