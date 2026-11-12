# La Tavola: Restaurant Reservation System

[![CI](https://github.com/Sotnuk11/restaurant-reservation/actions/workflows/ci.yml/badge.svg)](https://github.com/Sotnuk11/restaurant-reservation/actions/workflows/ci.yml)

A full-stack table reservation system for a restaurant: guests register, see which tables are free for a date, time and party size, and book; admins manage tables and see every reservation and basic statistics.
**Python / Flask / PostgreSQL** REST API with a vanilla JavaScript frontend (Polish, Ukrainian and English, light and dark theme).

## Features

- Registration and login (bcrypt, JWT with 8 h expiry), roles `client` and `admin`
- Live availability search by date, time and number of guests
- Reservations with validation, a per-user daily limit and cancellation
- Admin panel: add or remove tables, all reservations, statistics
- 14 automated API tests that run in CI

## Highlight: double booking is prevented by the database

Checking "is the table free?" and then inserting is a race condition: two simultaneous requests can both pass the check.
`SELECT ... FOR UPDATE` does not help when no row exists yet, so there is nothing to lock.
This project enforces the rule where it cannot be bypassed, with a **partial unique index** on confirmed reservations:

```sql
CREATE UNIQUE INDEX uq_confirmed_slot ON reservations (table_id, date, time) WHERE status = 'confirmed';
```

The API catches the `IntegrityError` and answers `409 Conflict`. Cancelling a reservation frees the slot again (covered by a test).

## Security

| Threat | Mitigation |
|---|---|
| SQL injection | SQLAlchemy ORM, parameterized queries only |
| XSS | Server-side validation of names; all user text rendered through an `escapeHTML` helper |
| Brute force and spam | Flask-Limiter: 10 logins / minute, 5 registrations / hour per IP; max 2 active bookings per user per day |
| Privilege escalation | Admin routes use an `admin_required` decorator; registration ignores any `role` in the request |
| Reading others' data | Cancelling or viewing another user's reservation returns 404 (ids cannot be probed) |
| User enumeration on login | One generic 401 message, and bcrypt runs for unknown e-mails too |
| Weak configuration | App refuses to start without `DATABASE_URL` and a `JWT_SECRET_KEY` of 32+ characters; CORS limited to configured origins |
| Oversized input | 16 KB request limit, strict type and length checks on every field |
| Secrets | `.env` is git-ignored; `.env.example` lists the variables |

**Known limitations:** the JWT is stored in `localStorage` (an `HttpOnly` cookie would be stronger against XSS), there are no refresh tokens or e-mail confirmation, and the rate limiter uses in-memory storage (use Redis with several workers).

## Run locally

Requirements: Python 3.11+, PostgreSQL.

```bash
# database
psql -d your_db -f database/schema.sql
psql -d your_db -f database/seed.sql        # sample tables

# backend
cd backend
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                # fill DATABASE_URL and JWT_SECRET_KEY
python app.py                                       # http://localhost:5000

# create the first admin (registration always creates clients)
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='at-least-12-characters' python create_admin.py

# frontend (in another terminal)
cd frontend && python -m http.server 3000           # http://localhost:3000
```

For production run `gunicorn wsgi:app`. Set the API address for the frontend in `frontend/config.js`.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Tests use a temporary SQLite database and cover validation, authentication, authorization, double booking, the daily limit and the admin flow.

## API

All responses look like `{ "status": "success" | "error", "message": "...", "data": ... }`. 🔒 needs `Authorization: Bearer <token>`, 👑 needs the admin role.

| Method | Path | Access |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | public |
| GET | `/api/auth/me` | 🔒 |
| GET | `/api/tables` | public |
| GET | `/api/tables/available?date=YYYY-MM-DD&time=HH:MM&guests=N` | 🔒 |
| POST, DELETE | `/api/tables`, `/api/tables/{id}` | 👑 |
| POST | `/api/reservations` | 🔒 |
| GET | `/api/reservations/my` | 🔒 |
| PATCH | `/api/reservations/{id}/cancel` | 🔒 (own) or 👑 |
| GET | `/api/reservations`, `/api/stats` | 👑 |

## Project structure

```
backend/     Flask API (app.py), tests, wsgi.py, create_admin.py
database/    schema.sql, seed.sql
frontend/    index.html, app.js, style.css, config.js
.github/     CI workflow
```

## Tech stack

Python, Flask, SQLAlchemy, PostgreSQL, Flask-JWT-Extended, Flask-Bcrypt, Flask-Limiter, pytest, JavaScript, HTML/CSS.

## License

MIT
