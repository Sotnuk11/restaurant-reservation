"""La Tavola: restaurant table reservation API.

Stack: Flask, SQLAlchemy (PostgreSQL), Flask-JWT-Extended, Flask-Bcrypt, Flask-Limiter.
User-facing messages are in Polish (the target restaurant is in Poland); code and comments are in English.
"""
import os
import re
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from sqlalchemy.exc import IntegrityError

load_dotenv()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NAME_RE = re.compile(r"^[A-Za-zЀ-ӿĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9\s\-']+$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):(00|30)$")  # bookings start on a 30-minute grid
MAX_BOOKINGS_PER_DAY = 2


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


# ---------- models ----------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(128), nullable=False)  # bcrypt hash
    role = db.Column(db.String(10), default="client", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    reservations = db.relationship("Reservation", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "phone": self.phone,
                "role": self.role, "created_at": self.created_at.isoformat()}


class Table(db.Model):
    __tablename__ = "tables"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), default="")
    active = db.Column(db.Boolean, default=True)
    reservations = db.relationship("Reservation", back_populates="table", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "number": self.number, "capacity": self.capacity,
                "location": self.location, "active": self.active}


class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    notes = db.Column(db.String(300), default="")
    status = db.Column(db.String(12), default="confirmed", nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User", back_populates="reservations")
    table = db.relationship("Table", back_populates="reservations")

    # The database itself guarantees "one confirmed booking per table and slot".
    # A SELECT ... FOR UPDATE alone cannot do this: when no row exists yet there is nothing to lock.
    __table_args__ = (
        Index("uq_confirmed_slot", "table_id", "date", "time", unique=True,
              postgresql_where=db.text("status = 'confirmed'"),
              sqlite_where=db.text("status = 'confirmed'")),
    )

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "user_name": self.user.name if self.user else None,
            "table_id": self.table_id, "table_number": self.table.number if self.table else None,
            "table_location": self.table.location if self.table else None, "date": self.date.isoformat(),
            "time": self.time, "guests": self.guests, "guest_name": self.guest_name,
            "phone": self.phone, "notes": self.notes, "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# ---------- helpers ----------
def normalize_phone(phone):
    """Keep digits only and prefix with '+'. Returns None when the number is not plausible (9-15 digits)."""
    digits = re.sub(r"\D", "", phone or "")
    return "+" + digits if 9 <= len(digits) <= 15 else None


def success(data=None, msg="OK", code=200):
    body = {"status": "success", "message": msg}
    if data is not None:
        body["data"] = data
    return jsonify(body), code


def error(msg, code=400):
    return jsonify({"status": "error", "message": msg}), code


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get("role") != "admin":
            return error("Brak uprawnień administratora", 403)
        return fn(*args, **kwargs)
    return wrapper


def positive_int(value):
    """Return value as a positive int, or None (also rejects bools, floats and junk strings)."""
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8),
        MAX_CONTENT_LENGTH=16 * 1024,
        RATELIMIT_ENABLED=True,
    )
    if config:
        app.config.update(config)

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("DATABASE_URL is not set")
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("postgres://"):  # old Heroku/Neon style prefix
        app.config["SQLALCHEMY_DATABASE_URI"] = uri.replace("postgres://", "postgresql://", 1)
    secret = app.config["JWT_SECRET_KEY"]
    if not secret or len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be set and at least 32 characters long")

    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
    CORS(app, origins=origins)
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    register_routes(app)
    return app


def register_routes(app):
    @app.errorhandler(413)
    def too_large(_):
        return error("Zbyt duże żądanie", 413)

    @app.errorhandler(429)
    def rate_limited(_):
        return error("Zbyt wiele prób. Spróbuj ponownie później.", 429)

    @app.errorhandler(500)
    def server_error(_):
        return error("Błąd serwera", 500)

    # ----- auth -----
    @app.post("/api/auth/register")
    @limiter.limit("5 per hour")
    def register():
        body = request.get_json(silent=True) or {}
        name = str(body.get("name") or "").strip()
        email = str(body.get("email") or "").strip().lower()
        phone = normalize_phone(str(body.get("phone") or ""))
        pwd = str(body.get("password") or "")

        if not (2 <= len(name) <= 50) or not NAME_RE.match(name):
            return error("Nieprawidłowe imię (2-50 znaków, bez znaków specjalnych)")
        if len(email) > 120 or not EMAIL_RE.match(email):
            return error("Nieprawidłowy format e-mail")
        if not phone:
            return error("Nieprawidłowy format telefonu")
        if not (8 <= len(pwd) <= 72):  # bcrypt only uses the first 72 bytes
            return error("Hasło: 8-72 znaków")
        if User.query.filter_by(email=email).first():
            return error("Konto z tym e-mailem już istnieje", 409)
        if User.query.filter_by(phone=phone).first():
            return error("Konto z tym numerem telefonu już istnieje", 409)

        user = User(name=name, email=email, phone=phone, password=bcrypt.generate_password_hash(pwd).decode("utf-8"))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return error("Konto już istnieje", 409)
        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        return success({"token": token, "user": user.to_dict()}, "Konto utworzone", 201)

    @app.post("/api/auth/login")
    @limiter.limit("10 per minute")
    def login():
        body = request.get_json(silent=True) or {}
        email = str(body.get("email") or "").strip().lower()
        pwd = str(body.get("password") or "")
        user = User.query.filter_by(email=email).first()
        # Hash a dummy value for unknown users so response time does not reveal which e-mails exist.
        hashed = user.password if user else DUMMY_HASH
        valid = bcrypt.check_password_hash(hashed, pwd)
        if not user or not valid:
            return error("Nieprawidłowy e-mail lub hasło", 401)
        token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
        return success({"token": token, "user": user.to_dict()})

    @app.get("/api/auth/me")
    @jwt_required()
    def me():
        user = db.session.get(User, int(get_jwt_identity()))
        if not user:
            return error("Użytkownik nie istnieje", 404)
        return success(user.to_dict())

    # ----- tables -----
    @app.get("/api/tables")
    def get_tables():
        return success([t.to_dict() for t in Table.query.filter_by(active=True).order_by(Table.number).all()])

    @app.get("/api/tables/available")
    @jwt_required()
    def get_available_tables():
        res_date, res_time = request.args.get("date"), request.args.get("time")
        guests = positive_int(request.args.get("guests", "1"))
        if not res_date or not res_time or not TIME_RE.match(res_time) or not guests:
            return error("Nieprawidłowa data, godzina lub liczba gości")
        try:
            d = date.fromisoformat(res_date)
        except ValueError:
            return error("Błąd formatu daty")

        booked = {row[0] for row in db.session.query(Reservation.table_id).filter(
            Reservation.date == d, Reservation.time == res_time, Reservation.status == "confirmed").all()}
        result = []
        for t in Table.query.filter_by(active=True).order_by(Table.number).all():
            info = t.to_dict()
            info["booked"] = t.id in booked
            info["available"] = t.id not in booked and t.capacity >= guests
            result.append(info)
        return success(result)

    @app.post("/api/tables")
    @admin_required
    def create_table():
        body = request.get_json(silent=True) or {}
        number, capacity = positive_int(body.get("number")), positive_int(body.get("capacity"))
        location = str(body.get("location") or "").strip()[:100]
        if not number or not capacity or capacity > 50:
            return error("Nieprawidłowy numer lub pojemność stolika")
        existing = Table.query.filter_by(number=number).first()
        if existing and existing.active:
            return error(f"Stolik {number} już istnieje", 409)
        if existing:  # a previously removed table with this number is reactivated, history is kept
            existing.active, existing.capacity, existing.location = True, capacity, location
            db.session.commit()
            return success(existing.to_dict(), "Stolik przywrócony", 201)
        table = Table(number=number, capacity=capacity, location=location)
        db.session.add(table)
        db.session.commit()
        return success(table.to_dict(), "Stolik dodany", 201)

    @app.delete("/api/tables/<int:tid>")
    @admin_required
    def delete_table(tid):
        table = db.session.get(Table, tid)
        if not table:
            return error("Stolik nie istnieje", 404)
        # Soft delete: the table disappears from the UI but past reservations stay in the history.
        # Upcoming confirmed reservations are cancelled so nobody is expected at a table that no longer exists.
        table.active = False
        Reservation.query.filter(Reservation.table_id == tid, Reservation.status == "confirmed",
                                 Reservation.date >= date.today()).update({"status": "cancelled"})
        db.session.commit()
        return success(msg="Usunięto")

    # ----- reservations -----
    @app.post("/api/reservations")
    @jwt_required()
    def create_reservation():
        uid = int(get_jwt_identity())
        body = request.get_json(silent=True) or {}
        table_id, guests = positive_int(body.get("table_id")), positive_int(body.get("guests"))
        res_time = str(body.get("time") or "")
        guest_name = str(body.get("guest_name") or "").strip()
        phone = normalize_phone(str(body.get("phone") or ""))
        notes = str(body.get("notes") or "").strip()

        if not table_id or not guests:
            return error("Nieprawidłowy stolik lub liczba gości")
        if not (2 <= len(guest_name) <= 100) or not NAME_RE.match(guest_name):
            return error("Nieprawidłowe imię gościa")
        if not phone:
            return error("Zły format telefonu")
        if len(notes) > 300:
            return error("Uwagi: max 300 znaków")
        if not TIME_RE.match(res_time):
            return error("Zły format godziny (HH:MM)")
        try:
            d = date.fromisoformat(str(body.get("date") or ""))
        except ValueError:
            return error("Zły format daty")
        if datetime.combine(d, datetime.strptime(res_time, "%H:%M").time()) < datetime.now():
            return error("Nie można rezerwować w przeszłości")

        if Reservation.query.filter_by(user_id=uid, date=d, status="confirmed").count() >= MAX_BOOKINGS_PER_DAY:
            return error("Przekroczono limit: max 2 aktywne rezerwacje na ten dzień.", 429)

        table = db.session.get(Table, table_id)
        if not table or not table.active:
            return error("Stolik nie istnieje", 404)
        if guests > table.capacity:
            return error(f"Stolik mieści max {table.capacity} os.")

        reservation = Reservation(user_id=uid, table_id=table_id, date=d, time=res_time, guests=guests,
                                  guest_name=guest_name, phone=phone, notes=notes)
        db.session.add(reservation)
        try:
            db.session.commit()
        except IntegrityError:  # the unique index rejected a concurrent double booking
            db.session.rollback()
            return error("Zajęte w tym terminie", 409)
        return success(reservation.to_dict(), "Rezerwacja potwierdzona", 201)

    @app.get("/api/reservations/my")
    @jwt_required()
    def my_reservations():
        uid = int(get_jwt_identity())
        rows = Reservation.query.filter_by(user_id=uid).order_by(Reservation.date.desc(), Reservation.time.desc()).all()
        return success([r.to_dict() for r in rows])

    @app.get("/api/reservations")
    @admin_required
    def all_reservations():
        rows = Reservation.query.order_by(Reservation.date.asc(), Reservation.time.asc()).all()
        return success([r.to_dict() for r in rows])

    @app.patch("/api/reservations/<int:rid>/cancel")
    @jwt_required()
    def cancel_reservation(rid):
        uid, claims = int(get_jwt_identity()), get_jwt()
        reservation = db.session.get(Reservation, rid)
        # Same answer for "missing" and "someone else's" so ids cannot be probed.
        if not reservation or (claims.get("role") != "admin" and reservation.user_id != uid):
            return error("Brak rezerwacji", 404)
        reservation.status = "cancelled"
        db.session.commit()
        return success(reservation.to_dict(), "Anulowano")

    # ----- stats -----
    @app.get("/api/stats")
    @admin_required
    def stats():
        today = date.today()
        total_tables = Table.query.filter_by(active=True).count()
        booked_today = {r[0] for r in db.session.query(Reservation.table_id).filter_by(date=today, status="confirmed").all()}
        return success({
            "total_confirmed": Reservation.query.filter_by(status="confirmed").count(),
            "today_confirmed": Reservation.query.filter_by(date=today, status="confirmed").count(),
            "total_tables": total_tables,
            "free_today": total_tables - len(booked_today),
            "total_users": User.query.count(),
        })


# Computed once at import time; used to equalize login timing for unknown users.
DUMMY_HASH = Bcrypt().generate_password_hash("dummy-password").decode("utf-8")

if __name__ == "__main__":
    application = create_app()
    application.run(debug=os.getenv("FLASK_ENV") == "development", port=int(os.getenv("PORT", 5000)))
