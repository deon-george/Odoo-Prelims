# Backend — Authentication & RBAC

FastAPI + SQLAlchemy + MySQL backend for the Subscription Management System.

Current status: **Stage 4 — registration, login, sessions, password reset, and role-based access control are implemented and tested.**

## Requirements

- Python 3.11+
- MySQL 8.0 running on `127.0.0.1:3306`

## 1. Create the databases and app user

Run as a MySQL administrator (for example `root`):

```sql
CREATE DATABASE IF NOT EXISTS odoo_prelims
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE DATABASE IF NOT EXISTS odoo_prelims_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'odoo_prelims'@'localhost'
  IDENTIFIED BY 'replace-with-a-strong-password';

GRANT ALL PRIVILEGES ON odoo_prelims.* TO 'odoo_prelims'@'localhost';
GRANT ALL PRIVILEGES ON odoo_prelims_test.* TO 'odoo_prelims'@'localhost';
FLUSH PRIVILEGES;
```

The app user only needs privileges on these two schemas.

## 2. Install dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Configure environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set at minimum:

- `DATABASE_URL` (and `TEST_DATABASE_URL`)
- `JWT_SECRET_KEY` — generate with
  `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` for the bootstrap admin

`.env` is git-ignored. Never commit real credentials.

## 4. Run migrations

```powershell
alembic upgrade head
```

This creates `users`, `refresh_tokens`, and `password_reset_tokens`.

To inspect the SQL without a live database:

```powershell
alembic upgrade head --sql
```

## 5. Verify the connection and create the admin

```powershell
python -m app.cli check-db
python -m app.cli create-admin
```

`create-admin` reads `ADMIN_FULL_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` from `.env`, or accepts flags:

```powershell
python -m app.cli create-admin --email admin@example.com --password 'Str0ng!Pass' --full-name 'Admin'
```

## 6. Run the API

```powershell
uvicorn app.main:app --reload --port 8000
```

- Health: <http://localhost:8000/api/health>
- OpenAPI docs: <http://localhost:8000/docs>

### Auth API

| Method | Path | Access |
|---|---|---|
| POST | `/api/auth/register` | Public (always creates a `customer`) |
| POST | `/api/auth/login` | Public |
| POST | `/api/auth/refresh` | Refresh cookie |
| POST | `/api/auth/logout` | Refresh cookie |
| GET | `/api/auth/me` | Authenticated |
| POST | `/api/auth/forgot-password` | Public (generic response) |
| POST | `/api/auth/reset-password` | Public (single-use token) |
| POST | `/api/admin/staff` | Admin |
| GET | `/api/admin/users` | Admin |
| PATCH | `/api/admin/users/{id}/status` | Admin (staff accounts only) |

The access token is a short-lived JWT returned to the browser and held in
memory. The rotating refresh token is an `HttpOnly` cookie and is stored only
as a SHA-256 hash in MySQL. Password-reset tokens are single-use, expire after
`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`, and are also stored hashed.

### Run the tests

```powershell
cd backend
pytest -q
```

Tests use `TEST_DATABASE_URL`; they never touch the development database.

## Layout

```text
backend/
├── app/
│   ├── core/          # settings, Argon2/JWT helpers, password policy
│   ├── db/            # declarative base, engine/session
│   ├── models/        # User, RefreshToken, PasswordResetToken
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # auth business logic + email delivery
│   ├── api/           # routers + RBAC dependencies
│   ├── cli.py         # check-db, create-admin, set-admin-credentials
│   └── main.py        # FastAPI app factory
├── alembic/           # migrations
├── tests/             # pytest auth/RBAC suite
└── requirements.txt
```

## Security notes

- Passwords are hashed with Argon2id; plaintext is never stored or logged.
- Refresh and password-reset tokens are stored only as SHA-256 hashes.
- Roles/status are stored in MySQL and re-checked per request in Stage 4.
- Secrets come from environment variables only.
