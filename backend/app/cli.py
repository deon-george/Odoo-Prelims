"""Management CLI.

Usage (from the backend/ directory, with the virtualenv active):

    python -m app.cli check-db
    python -m app.cli create-admin
    python -m app.cli create-admin --email admin@example.com --password '...' --full-name 'Admin'
    python -m app.cli set-admin-credentials
"""

from __future__ import annotations

import argparse
import getpass
import sys

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.password_policy import validate_password_strength
from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal, engine
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole, UserStatus


def check_db(_: argparse.Namespace) -> int:
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT VERSION()")).scalar_one()
    except Exception as exc:  # noqa: BLE001 - CLI should report, not traceback
        print(f"Database connection failed: {exc}", file=sys.stderr)
        return 1

    print(f"Database connection OK (MySQL {version}).")
    return 0


def create_admin(args: argparse.Namespace) -> int:
    email = (args.email or settings.admin_email or "").strip().lower()
    password = args.password or (
        settings.admin_password.get_secret_value() if settings.admin_password else ""
    )
    full_name = (args.full_name or settings.admin_full_name).strip()

    if not email:
        print("Missing admin email. Pass --email or set ADMIN_EMAIL.", file=sys.stderr)
        return 2
    if not password:
        print("Missing admin password. Pass --password or set ADMIN_PASSWORD.", file=sys.stderr)
        return 2
    if not full_name:
        print("Missing admin full name. Pass --full-name or set ADMIN_FULL_NAME.", file=sys.stderr)
        return 2

    policy_errors = validate_password_strength(password)
    if policy_errors:
        print("Password does not meet the policy:", file=sys.stderr)
        for error in policy_errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            print(
                f"An account with email {email!r} already exists (role={existing.role}).",
                file=sys.stderr,
            )
            return 1

        user = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print(f"An account with email {email!r} already exists.", file=sys.stderr)
            return 1

        db.refresh(user)
        print(f"Admin created: {user.email} (id={user.id}).")
        return 0


def _prompt_with_default(label: str, default: str) -> str | None:
    try:
        value = input(f"{label} [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    return value or default


def set_admin_credentials(args: argparse.Namespace) -> int:
    """Securely update the existing admin's email/password.

    The password is read with getpass (never echoed, never in argv, never in
    shell history or application logs). The command requires a real terminal.
    """
    if not sys.stdin.isatty():
        print(
            "This command requires an interactive terminal so the password is "
            "never echoed, stored in shell history, or written to logs.",
            file=sys.stderr,
        )
        return 2

    with SessionLocal() as db:
        admin: User | None = None
        if args.current_email:
            admin = db.scalar(
                select(User).where(User.email == args.current_email.strip().lower())
            )
        elif settings.admin_email:
            admin = db.scalar(
                select(User).where(User.email == settings.admin_email.strip().lower())
            )
        if admin is None:
            admin = db.scalar(
                select(User)
                .where(User.role == UserRole.ADMIN.value)
                .order_by(User.id)
            )
        if admin is None:
            print("No admin account found. Create one with `create-admin` first.", file=sys.stderr)
            return 1
        if admin.role != UserRole.ADMIN.value:
            print(f"Account {admin.email!r} is not an admin.", file=sys.stderr)
            return 1

        print(f"Updating admin: {admin.email} (id={admin.id})")

        new_email_raw = args.email
        if new_email_raw is None:
            new_email_raw = _prompt_with_default("New email", admin.email)
            if new_email_raw is None:
                print("\nAborted; no changes made.", file=sys.stderr)
                return 1
        try:
            new_email = validate_email(
                new_email_raw,
                check_deliverability=False,
            ).normalized.lower()
        except EmailNotValidError as exc:
            print(f"Invalid email: {exc}", file=sys.stderr)
            return 2

        new_full_name = args.full_name
        if new_full_name is None:
            new_full_name = _prompt_with_default("Full name", admin.full_name)
            if new_full_name is None:
                print("\nAborted; no changes made.", file=sys.stderr)
                return 1
        new_full_name = new_full_name.strip()
        if not 2 <= len(new_full_name) <= 150:
            print("Full name must be between 2 and 150 characters.", file=sys.stderr)
            return 2

        conflict = db.scalar(
            select(User).where(User.email == new_email, User.id != admin.id)
        )
        if conflict is not None:
            print(
                f"Email {new_email!r} is already in use by another account.",
                file=sys.stderr,
            )
            return 1

        try:
            password = getpass.getpass("New password: ")
            confirmation = getpass.getpass("Confirm new password: ")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted; no changes made.", file=sys.stderr)
            return 1

        if password != confirmation:
            print("Passwords do not match.", file=sys.stderr)
            return 2

        policy_errors = validate_password_strength(password)
        if policy_errors:
            print("Password does not meet the policy:", file=sys.stderr)
            for error in policy_errors:
                print(f"  - {error}", file=sys.stderr)
            return 2

        if not args.yes:
            try:
                answer = input("Apply these changes? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted; no changes made.", file=sys.stderr)
                return 1
            if answer not in {"y", "yes"}:
                print("Aborted; no changes made.")
                return 1

        new_hash = hash_password(password)
        if not verify_password(password, new_hash)[0]:
            print("Password verification failed; no changes made.", file=sys.stderr)
            return 1

        admin.email = new_email
        admin.full_name = new_full_name
        admin.hashed_password = new_hash
        revoked = db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == admin.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=func.now())
        ).rowcount

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            print(
                f"Could not update the admin: email {new_email!r} is already in use.",
                file=sys.stderr,
            )
            return 1

        db.refresh(admin)
        if not verify_password(password, admin.hashed_password)[0]:
            print("Post-update verification failed.", file=sys.stderr)
            return 1

        print(f"Admin credentials updated and verified for {admin.email} (id={admin.id}).")
        print(f"Revoked active refresh tokens: {revoked}")
        print(
            "Note: ADMIN_EMAIL / ADMIN_PASSWORD in backend/.env are bootstrap-only "
            "and were not changed by this command."
        )
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    db_parser = subparsers.add_parser("check-db", help="Verify the MySQL connection.")
    db_parser.set_defaults(handler=check_db)

    admin_parser = subparsers.add_parser(
        "create-admin",
        help="Create the bootstrap admin account (idempotent check by email).",
    )
    admin_parser.add_argument("--email")
    admin_parser.add_argument("--password")
    admin_parser.add_argument("--full-name", dest="full_name")
    admin_parser.set_defaults(handler=create_admin)

    credentials_parser = subparsers.add_parser(
        "set-admin-credentials",
        help=(
            "Securely update the existing admin email/password. The password is "
            "prompted with getpass and never echoed or logged."
        ),
    )
    credentials_parser.add_argument(
        "--current-email",
        help="Existing admin email (defaults to ADMIN_EMAIL or the first admin).",
    )
    credentials_parser.add_argument("--email", help="New admin email.")
    credentials_parser.add_argument("--full-name", dest="full_name", help="New full name.")
    credentials_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the final confirmation prompt.",
    )
    credentials_parser.set_defaults(handler=set_admin_credentials)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
