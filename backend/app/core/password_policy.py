"""Shared password policy.

Kept independent of FastAPI/Pydantic so the CLI and request schemas can use
exactly the same rules. The frontend mirrors these rules in Zod.
"""

MIN_PASSWORD_LENGTH = 9  # requirement: strictly more than 8 characters
MAX_PASSWORD_LENGTH = 128

SPECIAL_CHARACTERS = set("!@#$%^&*()_+-=[]{}|;:'\",.<>/?~`\\")


def validate_password_strength(password: str) -> list[str]:
    """Return a list of human-readable policy violations (empty means valid)."""
    errors: list[str] = []

    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append("Password must be more than 8 characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(f"Password must be at most {MAX_PASSWORD_LENGTH} characters long.")
    if not any(char.isupper() for char in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(char.islower() for char in password):
        errors.append("Password must contain at least one lowercase letter.")
    if not any(char in SPECIAL_CHARACTERS for char in password):
        errors.append("Password must contain at least one special character.")
    if password != password.strip():
        errors.append("Password must not start or end with whitespace.")

    return errors
