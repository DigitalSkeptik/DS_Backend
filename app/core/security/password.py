import bcrypt

from app.core.config import get_settings

MIN_PASSWORD_LENGTH = 6


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(get_settings().security.password_bcrypt_rounds),
    ).decode()


def is_password_too_simple(password: str) -> bool | tuple[bool, str]:  # noqa: C901 PLR0911
    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            True,
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )  # Changed {} to ()

    if not any(char.isalpha() for char in password):
        return (True, "Password must contain at least one letter")  # Changed {} to ()

    if not any(char.isupper() for char in password):
        return (
            True,
            "Password must contain at least one capital letter",
        )  # Changed {} to ()

    if not any(char.isdigit() for char in password):
        return (
            True,
            "Password must contain at least one number",
        )  # Changed {} to ()

    if not any(char in "!@#$%^&*()_+=-" for char in password):
        return (
            True,
            "Password must contain at least one special character",
        )  # Changed {} to ()

    # Check for potential SQL injection patterns
    sql_injection_patterns = [
        "'",
        ";",
        "--",
        "/*",
        "*/",
        "xp_",
        "sp_",
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "SELECT",
        "UNION",
        "EXEC",
        "ALTER",
        "CREATE",
        "TRUNCATE",
    ]

    password_upper = password.upper()
    for pattern in sql_injection_patterns:
        if pattern in password_upper:
            return (True, "Password contains invalid characters")

    return False


DUMMY_PASSWORD = get_password_hash("")
