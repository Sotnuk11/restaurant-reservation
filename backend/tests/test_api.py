"""API tests on a throwaway SQLite database (no network, no real secrets)."""
from datetime import date, timedelta

import pytest

from app import Table, User, bcrypt, create_app, db

ADMIN_PASSWORD = "admin-password-123"
FUTURE = (date.today() + timedelta(days=3)).isoformat()


@pytest.fixture()
def client(tmp_path):
    app = create_app({
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "JWT_SECRET_KEY": "t" * 48,
        "RATELIMIT_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        db.session.add(User(name="Admin", email="admin@test.pl", role="admin",
                            password=bcrypt.generate_password_hash(ADMIN_PASSWORD).decode()))
        db.session.add_all([Table(number=1, capacity=2, location="Okno"), Table(number=2, capacity=6, location="VIP")])
        db.session.commit()
    return app.test_client()


def register(client, n, **over):
    body = {"name": f"User {n}", "email": f"user{n}@test.pl", "phone": f"+4850000000{n}", "password": "password-123"}
    body.update(over)
    return client.post("/api/auth/register", json=body)


def hdr(resp):
    return {"Authorization": "Bearer " + resp.get_json()["data"]["token"]}


def book(client, headers, table=1, time="19:00", guests=2, **over):
    body = {"table_id": table, "date": FUTURE, "time": time, "guests": guests, "guest_name": "Jan Kowalski", "phone": "+48500111222"}
    body.update(over)
    return client.post("/api/reservations", json=body, headers=headers)


def test_refuses_to_start_with_weak_secret(tmp_path):
    with pytest.raises(RuntimeError):
        create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'x.db'}", "JWT_SECRET_KEY": "short"})


def test_register_validation(client):
    assert register(client, 1, email="not-an-email").status_code == 400
    assert register(client, 1, password="short").status_code == 400
    assert register(client, 1, phone="123").status_code == 400
    assert register(client, 1, name="<script>").status_code == 400
    assert register(client, 1).status_code == 201
    assert register(client, 1).status_code == 409


def test_register_stores_hash_and_never_returns_it(client):
    data = register(client, 1).get_json()["data"]["user"]
    assert "password" not in data and data["role"] == "client"


def test_login_same_error_for_wrong_password_and_unknown_user(client):
    register(client, 1)
    bad = client.post("/api/auth/login", json={"email": "user1@test.pl", "password": "wrong-password"})
    ghost = client.post("/api/auth/login", json={"email": "ghost@test.pl", "password": "wrong-password"})
    assert bad.status_code == ghost.status_code == 401
    assert bad.get_json() == ghost.get_json()


def test_endpoints_require_token(client):
    assert client.get("/api/reservations/my").status_code == 401
    assert client.post("/api/reservations", json={}).status_code == 401
    assert client.get("/api/stats").status_code == 401


def test_client_cannot_use_admin_endpoints(client):
    user = hdr(register(client, 1))
    assert client.get("/api/stats", headers=user).status_code == 403
    assert client.get("/api/reservations", headers=user).status_code == 403
    assert client.post("/api/tables", json={"number": 9, "capacity": 4}, headers=user).status_code == 403
    assert client.delete("/api/tables/1", headers=user).status_code == 403


def test_registration_cannot_set_admin_role(client):
    resp = register(client, 1, role="admin")
    assert resp.get_json()["data"]["user"]["role"] == "client"


def test_double_booking_is_rejected_for_same_slot_but_allowed_after_cancel(client):
    a, b = hdr(register(client, 1)), hdr(register(client, 2))
    first = book(client, a)
    assert first.status_code == 201
    assert book(client, b).status_code == 409  # same table, date and time
    assert book(client, b, table=2).status_code == 201  # other table is fine
    rid = first.get_json()["data"]["id"]
    assert client.patch(f"/api/reservations/{rid}/cancel", headers=a).status_code == 200
    assert book(client, b).status_code == 201  # slot is free again


def test_booking_validation(client):
    h = hdr(register(client, 1))
    assert book(client, h, guests=5).status_code == 400  # table 1 seats 2
    assert book(client, h, guests="abc").status_code == 400
    assert book(client, h, time="25:99").status_code == 400
    assert book(client, h, time="19:05").status_code == 400  # only :00 and :30 start times
    assert book(client, h, guest_name="<script>alert(1)</script>").status_code == 400
    assert book(client, h, date="2020-01-01").status_code == 400  # past
    assert book(client, h, table=99).status_code == 404
    assert book(client, h, notes="x" * 301).status_code == 400


def test_daily_limit_of_two_bookings(client):
    h = hdr(register(client, 1))
    assert book(client, h, time="12:00").status_code == 201
    assert book(client, h, time="14:00").status_code == 201
    assert book(client, h, time="16:00").status_code == 429


def test_cannot_cancel_someone_elses_reservation(client):
    a, b = hdr(register(client, 1)), hdr(register(client, 2))
    rid = book(client, a).get_json()["data"]["id"]
    assert client.patch(f"/api/reservations/{rid}/cancel", headers=b).status_code == 404
    assert [r["id"] for r in client.get("/api/reservations/my", headers=b).get_json()["data"]] == []


def test_admin_flow(client):
    admin = hdr(client.post("/api/auth/login", json={"email": "admin@test.pl", "password": ADMIN_PASSWORD}))
    assert client.post("/api/tables", json={"number": 9, "capacity": 4, "location": "Taras"}, headers=admin).status_code == 201
    assert client.post("/api/tables", json={"number": 9, "capacity": 4}, headers=admin).status_code == 409
    assert client.post("/api/tables", json={"number": "x", "capacity": 4}, headers=admin).status_code == 400
    stats = client.get("/api/stats", headers=admin).get_json()["data"]
    assert stats["total_tables"] == 3 and stats["total_users"] == 1


def test_availability_marks_booked_and_too_small_tables(client):
    h = hdr(register(client, 1))
    book(client, h, table=1)
    data = client.get(f"/api/tables/available?date={FUTURE}&time=19:00&guests=4", headers=h).get_json()["data"]
    by_number = {t["number"]: t for t in data}
    assert by_number[1]["booked"] and not by_number[1]["available"]
    assert by_number[2]["available"]
    assert client.get(f"/api/tables/available?date={FUTURE}&time=bad&guests=2", headers=h).status_code == 400


def test_unknown_route_and_bad_json_do_not_crash(client):
    assert client.post("/api/auth/login", data="{bad", content_type="application/json").status_code == 401
    assert client.get("/api/nope").status_code == 404


def test_deleting_a_table_keeps_history_and_cancels_upcoming_bookings(client):
    admin = hdr(client.post("/api/auth/login", json={"email": "admin@test.pl", "password": ADMIN_PASSWORD}))
    user = hdr(register(client, 1))
    rid = book(client, user, table=1).get_json()["data"]["id"]
    assert client.delete("/api/tables/1", headers=admin).status_code == 200
    assert 1 not in [t["number"] for t in client.get("/api/tables").get_json()["data"]]
    mine = client.get("/api/reservations/my", headers=user).get_json()["data"]
    assert [(r["id"], r["status"]) for r in mine] == [(rid, "cancelled")]  # history kept, booking cancelled
    # the same number can be added again and is reactivated
    assert client.post("/api/tables", json={"number": 1, "capacity": 4}, headers=admin).status_code == 201
