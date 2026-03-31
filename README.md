# Bill Reminder Bot

A personal Telegram bot that tracks monthly bills and sends daily reminders before they are due.

## Features

- Add bills with a name, amount, currency, and due day (1–28)
- Daily reminders at 09:00 (configurable timezone) — 7 days, 3 days, and 1 day before due
- Mark bills as paid via inline keyboard
- View payment history grouped by month (last 6 months)
- Reminder deduplication — each reminder is sent exactly once per cycle
- Migrations run automatically on startup

## Commands

| Command | Description |
|---|---|
| `/start` | Register and see the command list |
| `/addbill` | Add a new bill (guided conversation) |
| `/bills` | List all active bills |
| `/delbill` | Delete a bill (inline keyboard) |
| `/paid` | Mark a bill as paid for the current cycle |
| `/history` | Payment history for the last 6 months |

## Stack

| Layer | Technology |
|---|---|
| Bot framework | python-telegram-bot v22 with APScheduler job queue |
| Database | PostgreSQL 17 via SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic (auto-applied on startup) |
| Config | pydantic-settings v2 |
| Runtime | Python 3.14, uv |
| Containerisation | Docker + Docker Compose |
| Linting / formatting | ruff |
| Task runner | Poe the Poet |
| CI | GitHub Actions (ruff check + format) |

## Project Structure

```
bill-reminder-bot/
├── src/bot/
│   ├── channels/          # Abstracted notification channels
│   │   ├── base.py        # BaseChannel ABC
│   │   └── telegram.py    # TelegramChannel implementation
│   ├── db/
│   │   ├── connection.py  # Async engine + session factory
│   │   └── models.py      # SQLAlchemy ORM models
│   ├── handlers/          # PTB command/callback handlers
│   │   ├── bills.py       # /addbill, /bills, /delbill
│   │   ├── errors.py      # Global error handler
│   │   ├── history.py     # /history
│   │   ├── payments.py    # /paid
│   │   └── start.py       # /start
│   ├── services/          # Business logic layer
│   │   ├── bills.py       # User + bill CRUD
│   │   └── payments.py    # Payments, reminders, history
│   ├── bot.py             # Application builder
│   ├── config.py          # pydantic Settings
│   ├── main.py            # Entry point
│   ├── notifier.py        # Per-user reminder logic
│   ├── scheduler.py       # Daily APScheduler job
│   └── utils.py           # Pure date/format helpers
├── migrations/
│   ├── env.py             # Async Alembic environment
│   └── versions/
│       └── 20260331_initial.py
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── helpers.py         # make_session() mock helper
│   ├── test_notifier.py
│   ├── test_services_bills.py
│   ├── test_services_payments.py
│   └── test_utils.py
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Database Schema

```
users
  id           UUID  PK
  telegram_id  INT   UNIQUE
  username     TEXT
  created_at   TIMESTAMPTZ

bills
  id            UUID  PK
  user_id       UUID  FK → users (CASCADE)
  name          TEXT
  amount        NUMERIC(10,2)
  currency      TEXT  default 'USD'
  due_day       SMALLINT  CHECK (1–28)
  reminder_days INT[]  default {7,3,1}
  enabled       BOOL  default true
  created_at    TIMESTAMPTZ

payments
  id          UUID  PK
  bill_id     UUID  FK → bills (CASCADE)
  user_id     UUID  FK → users
  cycle_key   TEXT  (e.g. '2026-04')  UNIQUE with bill_id
  due_date    DATE
  paid_date   DATE
  amount      NUMERIC(10,2)
  status      TEXT  ('pending' | 'paid' | 'missed')
  created_at  TIMESTAMPTZ

reminder_log
  id          UUID  PK
  bill_id     UUID  FK → bills (CASCADE)
  due_date    DATE
  channel     TEXT
  offset_days INT
  sent_at     TIMESTAMPTZ
  UNIQUE (bill_id, due_date, channel, offset_days)
```

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A Telegram bot token — create one via [@BotFather](https://t.me/BotFather)

### 1. Clone and configure

```bash
git clone <repo-url>
cd bill-reminder-bot
cp .env.example .env
```

Edit `.env` and fill in your values:

```dotenv
TELEGRAM_BOT_TOKEN=your-bot-token-here

POSTGRES_USER=billbot
POSTGRES_PASSWORD=billbot
POSTGRES_DB=billbot
DATABASE_URL=postgresql+asyncpg://billbot:billbot@postgres:5432/billbot

# Timezone for reminders (IANA name). Default: UTC+3
BOT_TIMEZONE=Etc/GMT-3
```

### 2. Start

```bash
uv run poe build   # build the bot image
uv run poe up      # start bot + postgres
```

The bot applies Alembic migrations automatically on startup, then begins polling.

### 3. Verify

Open Telegram, find your bot, and send `/start`. The bot should reply with a welcome message and a users row will appear in the `users` table.

## Development

### Install dependencies

```bash
uv sync
```

### Run tasks with Poe

```bash
uv run poe <task>
```

| Task | Description |
|---|---|
| `test` | Run all tests with coverage |
| `test-fast` | Run tests without coverage, stop on first failure |
| `lint` | Check code with ruff |
| `lint-fix` | Auto-fix ruff lint issues |
| `format` | Format code with ruff |
| `format-check` | Check formatting without modifying files |
| `check` | Run lint + format check + tests (CI equivalent) |
| `build` | Build the bot Docker image |
| `up` | Start all services in detached mode |
| `down` | Stop all services |
| `logs` | Tail bot container logs |
| `migrate` | Apply migrations inside the container |
| `db-reset` | Stop services, restart postgres, re-apply migrations |

### Run tests

```bash
uv run poe test
```

Tests use mocked `AsyncSession` — no database or running bot required. The `asyncio_mode = "auto"` setting in `pyproject.toml` means all async tests run without any extra decoration.

```
tests/test_utils.py            — pure date/format functions
tests/test_services_bills.py   — user + bill CRUD
tests/test_services_payments.py — payment lifecycle, due-bill logic
tests/test_notifier.py         — reminder formatting + notify flow
```

### Alembic migrations

Migrations run automatically when the bot starts. To run them manually against a local database:

```bash
# start only postgres
docker compose up -d postgres

# apply migrations (uses DATABASE_URL from .env, pointing at localhost:5432)
uv run alembic upgrade head
```

To generate a new migration after changing a model:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

### Pre-commit hooks

```bash
uvx pre-commit install
```

Runs `ruff check --fix` and `ruff format` on every commit.

## Configuration Reference

All settings are read from environment variables (or `.env`).

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `DATABASE_URL` | Yes | — | asyncpg connection string |
| `POSTGRES_USER` | Yes | — | Used by Docker Compose to create the DB |
| `POSTGRES_PASSWORD` | Yes | — | Used by Docker Compose |
| `POSTGRES_DB` | Yes | — | Used by Docker Compose |
| `BOT_TIMEZONE` | No | `Etc/GMT-3` | IANA timezone for due dates and the 09:00 reminder job |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

## CI

GitHub Actions runs on every push and pull request:

- `ruff check` — lint
- `ruff format --check` — formatting

See `.github/workflows/lint.yml`.
