import random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import api_messages, deps
from app.models import CompletedModule, Module, Question, Test, User
from app.schemas.requests import TestAnswerRequest, TestSubmissionRequest
from app.schemas.responses import (
    AnswerOptionResponse,
    CorrectAnswerResponse,
    ModuleTestStatusResponse,
    QuestionResponse,
    QuestionResultResponse,
    TestResponse,
    TestSubmissionResponse,
)

router = APIRouter()

TEST_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "Test or module not found",
        "content": {
            "application/json": {
                "examples": {
                    "test not found": {
                        "summary": api_messages.TEST_NOT_FOUND,
                        "value": {"detail": api_messages.TEST_NOT_FOUND},
                    },
                    "module not found": {
                        "summary": api_messages.MODULE_NOT_FOUND,
                        "value": {"detail": api_messages.MODULE_NOT_FOUND},
                    },
                    "no test": {
                        "summary": api_messages.TEST_MODULE_HAS_NO_TEST,
                        "value": {"detail": api_messages.TEST_MODULE_HAS_NO_TEST},
                    },
                }
            }
        },
    },
    403: {
        "description": "Access denied",
        "content": {
            "application/json": {"example": {"detail": api_messages.TEST_ACCESS_DENIED}}
        },
    },
}

SUBMIT_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Invalid submission",
        "content": {
            "application/json": {
                "examples": {
                    "invalid submission": {
                        "summary": api_messages.TEST_INVALID_SUBMISSION,
                        "value": {"detail": api_messages.TEST_INVALID_SUBMISSION},
                    },
                    "invalid option": {
                        "summary": api_messages.TEST_INVALID_OPTION,
                        "value": {"detail": api_messages.TEST_INVALID_OPTION},
                    },
                }
            }
        },
    },
    404: {
        "description": "Test not found",
        "content": {
            "application/json": {"example": {"detail": api_messages.TEST_NOT_FOUND}}
        },
    },
    403: {
        "description": "Access denied",
        "content": {
            "application/json": {"example": {"detail": api_messages.TEST_ACCESS_DENIED}}
        },
    },
}

PASSING_THRESHOLD = 70


@router.get(
    "/module/{module_id}",
    response_model=TestResponse,
    responses=TEST_RESPONSES,
    summary="Получить тест модуля",
    response_description="Тест с вопросами и вариантами ответов",
)
async def get_module_test(
    module_id: str,
    module: Module = Depends(deps.get_module_with_access_check),
    session: AsyncSession = Depends(deps.get_session),
) -> TestResponse:
    """
    Получить тест для модуля с рандомизированными вопросами.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен
    - **Покупка курса**: Пользователь должен купить курс
    - **Наличие теста**: Модуль должен иметь тест

    ## Особенности

    - **Рандомизация**: Вопросы перемешиваются при каждом запросе
    - **Без правильных ответов**: Правильные ответы не показываются
    - **Stateless**: Не сохраняет состояние прохождения

    ## Возвращаемые данные

    ### Информация о тесте
    - `test_id` - уникальный идентификатор теста
    - `module_id` - ID модуля
    - `title` - название теста
    - `description` - описание теста

    ### Вопросы
    - `questions` - массив вопросов (порядок рандомизирован)
      - `question_id` - ID вопроса
      - `question_text` - текст вопроса
      - `answer_options` - варианты ответов
        - `option_id` - ID варианта ответа
        - `answer_text` - текст варианта ответа

    **Примечание**: Поле `is_correct` не включается в ответ для предотвращения читерства.

    ## Процесс прохождения теста

    1. Получить тест (этот эндпоинт)
    2. Пользователь отвечает на вопросы
    3. Отправить ответы через `POST /tests/{test_id}/submit`
    4. Получить результаты с правильными ответами

    ## Примеры использования

    ```bash
    # Получить тест модуля
    GET /api/v2/tests/module/{module_id}
    Authorization: Bearer <token>
    ```

    ## Ошибки

    - **401 Unauthorized**: Не авторизован
    - **403 Forbidden**: Курс не куплен
    - **404 Not Found**:
      - Модуль не найден
      - У модуля нет теста
    """
    test = await session.scalar(
        select(Test)
        .options(selectinload(Test.questions).selectinload(Question.answer_options))
        .where(Test.module_id == module_id)
    )

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_MODULE_HAS_NO_TEST,
        )

    questions = list(test.questions)
    random.shuffle(questions)

    return TestResponse(
        test_id=test.unique_id,
        module_id=test.module_id,
        title=test.title,
        description=test.description,
        questions=[
            QuestionResponse(
                question_id=q.unique_id,
                question_text=q.question_text,
                answer_options=[
                    AnswerOptionResponse(
                        option_id=opt.unique_id, answer_text=opt.answer_text
                    )
                    for opt in q.answer_options
                ],
            )
            for q in questions
        ],
    )


@router.post(
    "/{test_id}/answer",
    response_model=QuestionResultResponse,
    responses=SUBMIT_RESPONSES,
    summary="Проверить один ответ",
    response_description="Результат проверки ответа с объяснением",
)
async def check_single_answer(
    test_id: str,
    data: TestAnswerRequest,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> QuestionResultResponse:
    """
    Проверить правильность одного ответа (stateless режим).

    ## Описание

    Позволяет проверить правильность ответа на отдельный вопрос без отправки всего теста.
    Полезно для интерактивного обучения с немедленной обратной связью.

    ## Особенности

    - **Stateless**: Не сохраняет прогресс прохождения теста
    - **Немедленная обратная связь**: Сразу показывает правильный ответ
    - **С объяснением**: Включает объяснение правильного ответа
    - **Не влияет на завершение**: Не засчитывается как прохождение теста

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен
    - **Покупка курса**: Пользователь должен купить курс

    ## Входные данные

    - `question_id` - ID вопроса из теста
    - `selected_option_id` - ID выбранного варианта ответа

    ## Возвращаемые данные

    - `question_id` - ID вопроса
    - `question_text` - текст вопроса
    - `selected_option_id` - ID выбранного ответа
    - `is_correct` - правильный ли ответ (true/false)
    - `correct_option` - информация о правильном ответе
      - `option_id` - ID правильного ответа
      - `answer_text` - текст правильного ответа
      - `explanation` - объяснение (если есть)

    ## Примеры использования

    ```bash
    # Проверить ответ на вопрос
    POST /api/v2/tests/{test_id}/answer
    Authorization: Bearer <token>
    Content-Type: application/json

    {
      "question_id": "question-uuid",
      "selected_option_id": "option-uuid"
    }
    ```

    ## Отличие от полной отправки теста

    - **Этот эндпоинт**: Проверяет один вопрос, не засчитывается
    - **POST /tests/{test_id}/submit**: Отправляет весь тест, засчитывается прохождение

    ## Ошибки

    - **400 Bad Request**:
      - Вопрос не принадлежит тесту
      - Неверный ID варианта ответа
    - **403 Forbidden**: Курс не куплен
    - **404 Not Found**: Тест не найден
    """
    test = await session.scalar(
        select(Test)
        .options(
            selectinload(Test.module).selectinload(Module.course),
            selectinload(Test.questions).selectinload(Question.answer_options),
        )
        .where(Test.unique_id == test_id)
    )
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=api_messages.TEST_NOT_FOUND,
        )

    has_access = await deps.verify_course_access(
        test.module.course_id, current_user, session
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.TEST_ACCESS_DENIED,
        )

    question = next(
        (q for q in test.questions if q.unique_id == data.question_id), None
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_INVALID_SUBMISSION,
        )

    selected_option = next(
        (o for o in question.answer_options if o.unique_id == data.selected_option_id),
        None,
    )
    if not selected_option:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_INVALID_OPTION,
        )

    correct_option = next((o for o in question.answer_options if o.is_correct), None)
    is_correct = bool(selected_option.is_correct)

    return QuestionResultResponse(
        question_id=question.unique_id,
        question_text=question.question_text,
        selected_option_id=data.selected_option_id,
        is_correct=is_correct,
        correct_option=CorrectAnswerResponse(
            option_id=correct_option.unique_id if correct_option else "",
            answer_text=correct_option.answer_text if correct_option else "",
            explanation=getattr(correct_option, "explanation", None)
            if correct_option
            else None,
        ),
    )


@router.post(
    "/{test_id}/submit",
    response_model=TestSubmissionResponse,
    responses=SUBMIT_RESPONSES,
    summary="Отправить тест на проверку",
    response_description="Результаты прохождения теста с оценкой",
)
async def submit_test(
    test_id: str,
    submission: TestSubmissionRequest,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> TestSubmissionResponse:
    """
    Отправить ответы на все вопросы теста и получить результаты.

    ## Описание

    Финальная отправка теста с проверкой всех ответов. При успешном прохождении
    (≥70% правильных ответов) модуль автоматически отмечается как завершенный.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен
    - **Покупка курса**: Пользователь должен купить курс
    - **Все вопросы**: Необходимо ответить на все вопросы теста

    ## Критерии прохождения

    - **Проходной балл**: 70% правильных ответов
    - **Завершение модуля**: Автоматически при первом успешном прохождении
    - **Повторное прохождение**: Можно проходить несколько раз

    ## Входные данные

    - `answers` - массив ответов на все вопросы
      - `question_id` - ID вопроса
      - `selected_option_id` - ID выбранного варианта ответа

    **Важно**: Должны быть ответы на ВСЕ вопросы теста, иначе будет ошибка 400.

    ## Возвращаемые данные

    ### Общие результаты
    - `test_id` - ID теста
    - `score_percentage` - процент правильных ответов (0-100)
    - `passed` - пройден ли тест (≥70%)
    - `passing_threshold` - проходной балл (70)
    - `total_questions` - всего вопросов
    - `correct_answers` - количество правильных ответов
    - `module_completed` - завершен ли модуль (true при первом прохождении)

    ### Детальные результаты
    - `results` - массив результатов по каждому вопросу
      - `question_id` - ID вопроса
      - `question_text` - текст вопроса
      - `selected_option_id` - выбранный ответ
      - `is_correct` - правильный ли ответ
      - `correct_option` - информация о правильном ответе
        - `option_id` - ID правильного ответа
        - `answer_text` - текст правильного ответа
        - `explanation` - объяснение

    ## Примеры использования

    ```bash
    # Отправить тест
    POST /api/v2/tests/{test_id}/submit
    Authorization: Bearer <token>
    Content-Type: application/json

    {
      "answers": [
        {
          "question_id": "question-1-uuid",
          "selected_option_id": "option-a-uuid"
        },
        {
          "question_id": "question-2-uuid",
          "selected_option_id": "option-b-uuid"
        }
      ]
    }
    ```

    ## Процесс прохождения

    1. Получить тест: `GET /tests/module/{module_id}`
    2. Пользователь отвечает на все вопросы
    3. Отправить ответы: `POST /tests/{test_id}/submit`
    4. Получить результаты с правильными ответами
    5. При успехе (≥70%) модуль автоматически завершается

    ## Ошибки

    - **400 Bad Request**:
      - Не все вопросы отвечены
      - Неверный ID вопроса или варианта ответа
    - **403 Forbidden**: Курс не куплен
    - **404 Not Found**: Тест не найден
    """
    test = await session.scalar(
        select(Test)
        .options(
            selectinload(Test.module).selectinload(Module.course),
            selectinload(Test.questions).selectinload(Question.answer_options),
        )
        .where(Test.unique_id == test_id)
    )

    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=api_messages.TEST_NOT_FOUND
        )

    has_access = await deps.verify_course_access(
        test.module.course_id, current_user, session
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=api_messages.TEST_ACCESS_DENIED,
        )

    question_ids = {q.unique_id for q in test.questions}
    submitted_ids = {ans.question_id for ans in submission.answers}

    if question_ids != submitted_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=api_messages.TEST_INVALID_SUBMISSION,
        )

    answer_map = {ans.question_id: ans.selected_option_id for ans in submission.answers}

    results = []
    correct_count = 0

    for question in test.questions:
        selected_id = answer_map[question.unique_id]

        selected_option = next(
            o for o in question.answer_options if o.unique_id == selected_id
        )
        correct_option = next(o for o in question.answer_options if o.is_correct)

        if not selected_option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_messages.TEST_INVALID_OPTION,
            )

        is_correct = selected_option.is_correct
        if is_correct:
            correct_count += 1

        results.append(
            QuestionResultResponse(
                question_id=question.unique_id,
                question_text=question.question_text,
                selected_option_id=selected_id,
                is_correct=is_correct,
                correct_option=CorrectAnswerResponse(
                    option_id=correct_option.unique_id,
                    answer_text=correct_option.answer_text,
                    explanation=correct_option.explanation,
                ),
            )
        )

    total_questions = len(test.questions)
    score_percentage = (correct_count / total_questions) * 100
    passed = score_percentage >= PASSING_THRESHOLD

    module_completed = False
    if passed:
        existing = await session.scalar(
            select(CompletedModule).where(
                CompletedModule.user_id == current_user.unique_id,
                CompletedModule.module_id == test.module_id,
            )
        )

        if not existing:
            completed = CompletedModule(
                user_id=current_user.unique_id, module_id=test.module_id
            )
            session.add(completed)
            await session.commit()
            module_completed = True

    return TestSubmissionResponse(
        test_id=test_id,
        score_percentage=round(score_percentage, 2),
        passed=passed,
        passing_threshold=PASSING_THRESHOLD,
        total_questions=total_questions,
        correct_answers=correct_count,
        module_completed=module_completed,
        results=results,
    )


@router.get(
    "/module/{module_id}/status",
    response_model=ModuleTestStatusResponse,
    summary="Получить статус теста модуля",
    response_description="Информация о наличии и прохождении теста",
)
async def get_module_test_status(
    module_id: str,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_session),
) -> ModuleTestStatusResponse:
    """
    Проверить статус прохождения теста модуля пользователем.

    ## Описание

    Возвращает информацию о том, есть ли у модуля тест и завершил ли
    его пользователь. Полезно для отображения прогресса обучения.

    ## Требования

    - **Авторизация обязательна**: Требуется JWT токен

    ## Возвращаемые данные

    - `module_id` - ID модуля
    - `has_test` - есть ли у модуля тест (true/false)
    - `completed` - завершен ли тест пользователем (true/false)
    - `completed_at` - дата и время завершения (ISO 8601, null если не завершен)

    ## Логика завершения

    Тест считается завершенным, если:
    - Пользователь отправил тест через `POST /tests/{test_id}/submit`
    - Набрал ≥70% правильных ответов
    - Модуль автоматически отмечен как завершенный

    ## Примеры использования

    ```bash
    # Проверить статус теста модуля
    GET /api/v2/tests/module/{module_id}/status
    Authorization: Bearer <token>
    ```

    ## Примеры ответов

    ### Модуль с завершенным тестом
    ```json
    {
      "module_id": "module-uuid",
      "has_test": true,
      "completed": true,
      "completed_at": "2024-01-15T10:30:00Z"
    }
    ```

    ### Модуль с незавершенным тестом
    ```json
    {
      "module_id": "module-uuid",
      "has_test": true,
      "completed": false,
      "completed_at": null
    }
    ```

    ### Модуль без теста
    ```json
    {
      "module_id": "module-uuid",
      "has_test": false,
      "completed": false,
      "completed_at": null
    }
    ```

    ## Использование в UI

    Этот эндпоинт полезен для:
    - Отображения прогресса курса
    - Показа бейджей "Завершено"
    - Блокировки следующих модулей до прохождения теста
    - Отображения даты завершения
    """
    test = await session.scalar(select(Test).where(Test.module_id == module_id))

    has_test = test is not None

    completed_module = await session.scalar(
        select(CompletedModule).where(
            CompletedModule.user_id == current_user.unique_id,
            CompletedModule.module_id == module_id,
        )
    )

    return ModuleTestStatusResponse(
        module_id=module_id,
        has_test=has_test,
        completed=completed_module is not None,
        completed_at=completed_module.create_time if completed_module else None,
    )
