import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_session import get_async_session
from app.models import IdempotencyKey

# Constants for idempotency key validation
MIN_IDEMPOTENCY_KEY_LENGTH = 3
MAX_IDEMPOTENCY_KEY_LENGTH = 255


def generate_body_hash(body: bytes | str) -> str:
    if isinstance(body, str):
        body = body.encode("utf-8")
    return hashlib.sha256(body).hexdigest()


async def get_idempotency_response(
    idempotency_key: str,
    session: AsyncSession,
) -> dict[str, Any] | None:
    await cleanup_expired_keys(session)

    result = await session.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.key == idempotency_key,
            IdempotencyKey.expires_at > datetime.utcnow(),
        )
    )

    if result:
        return {
            "status": result.response_status,
            "body": result.response_body,
        }
    return None


async def store_idempotency_response(  # noqa: PLR0913
    idempotency_key: str,
    request_path: str,
    request_method: str,
    request_body: bytes | str,
    response_status: int,
    response_body: dict[str, Any],
    session: AsyncSession,
    expires_hours: int = 24,
) -> None:
    body_hash = generate_body_hash(request_body)
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

    idempotency_record = IdempotencyKey(
        key=idempotency_key,
        request_path=request_path,
        request_method=request_method,
        request_body_hash=body_hash,
        response_status=response_status,
        response_body=response_body,
        expires_at=expires_at,
    )

    session.add(idempotency_record)
    await session.commit()


async def cleanup_expired_keys(session: AsyncSession) -> None:
    await session.execute(
        delete(IdempotencyKey).where(IdempotencyKey.expires_at <= datetime.utcnow())
    )
    await session.commit()


def validate_idempotency_key(idempotency_key: str | None) -> str:
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required for POST operations",
        )

    if (
        len(idempotency_key) < MIN_IDEMPOTENCY_KEY_LENGTH
        or len(idempotency_key) > MAX_IDEMPOTENCY_KEY_LENGTH
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Idempotency-Key must be between {MIN_IDEMPOTENCY_KEY_LENGTH} and {MAX_IDEMPOTENCY_KEY_LENGTH} characters",
        )

    return idempotency_key


async def check_body_hash_mismatch(
    idempotency_key: str,
    request_body: bytes | str,
    session: AsyncSession,
) -> bool:
    body_hash = generate_body_hash(request_body)

    result = await session.scalar(
        select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
    )

    if result and result.request_body_hash != body_hash:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body hash does not match stored idempotency key",
        )

    return False


class IdempotencyMiddleware:
    """Middleware to handle idempotency for POST operations"""

    def __init__(self, app: Any) -> None:  # type: ignore[no-untyped-def]
        self.app = app

    async def __call__(  # noqa: PLR0912, PLR0915
        self,
        scope: dict[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        idempotency_key = headers.get(b"idempotency-key", b"").decode()

        # If no idempotency key, proceed normally
        if not idempotency_key:
            await self.app(scope, receive, send)
            return
        try:
            validate_idempotency_key(idempotency_key)
        except HTTPException as e:
            await self._send_error_response(send, e.status_code, {"detail": e.detail})
            return

        # First, we need to fully receive the request body
        request_body = b""

        # Receive the full request body before checking cache
        while True:
            message = await receive()
            if message["type"] == "http.request":
                request_body += message.get("body", b"")
                if not message.get("more_body", False):
                    break

        async with get_async_session() as session:
            try:
                cached_response = await get_idempotency_response(
                    idempotency_key, session
                )
                if cached_response:
                    try:
                        await check_body_hash_mismatch(
                            idempotency_key, request_body, session
                        )
                    except HTTPException as e:
                        await self._send_error_response(
                            send, e.status_code, {"detail": e.detail}
                        )
                        return

                    await self._send_cached_response(send, cached_response)
                    return
            except Exception:
                # if there's any error with idempotency, we go with normal request
                pass

        # Now we need to replay the body to the application
        body_sent = False

        async def receive_wrapper() -> dict[str, Any]:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": request_body,
                    "more_body": False,
                }
            # If called again, return disconnect
            return {"type": "http.disconnect"}

        original_send = send
        response_data: dict[str, Any] = {"status": None, "body": b"", "headers": []}

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_data["status"] = message["status"]
                response_data["headers"] = message.get("headers", [])
            elif message["type"] == "http.response.body":
                response_data["body"] += message.get("body", b"")
            await original_send(message)

        # Process the request
        await self.app(scope, receive_wrapper, send_wrapper)

        # Store the response for future idempotency
        if response_data["status"] is not None:
            async with get_async_session() as session:
                try:
                    # Parse response body as JSON if possible
                    try:
                        response_body = json.loads(response_data["body"].decode())  # type: ignore[union-attr]
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        response_body = {"raw_response": response_data["body"].decode()}  # type: ignore[union-attr]

                    await store_idempotency_response(
                        idempotency_key=idempotency_key,
                        request_path=scope["path"],
                        request_method=scope["method"],
                        request_body=request_body,
                        response_status=response_data["status"],  # type: ignore[arg-type]
                        response_body=response_body,
                        session=session,
                    )
                except Exception:
                    # If storing fails, it's not critical
                    pass

    async def _send_error_response(
        self, send: Callable[..., Any], status_code: int, body: dict[str, Any]
    ) -> None:  # type: ignore[type-arg]
        """Send error response"""
        body_json = json.dumps(body).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body_json)).encode()],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body_json,
            }
        )

    async def _send_cached_response(
        self, send: Callable[..., Any], cached_response: dict[str, Any]
    ) -> None:  # type: ignore[type-arg]
        """Send cached response"""
        body_json = json.dumps(cached_response["body"]).encode()
        await send(
            {
                "type": "http.response.start",
                "status": cached_response["status"],
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body_json)).encode()],
                    [b"x-idempotency-cached", b"true"],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body_json,
            }
        )
