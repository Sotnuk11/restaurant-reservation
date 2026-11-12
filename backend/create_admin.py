"""Create (or promote) an admin: ADMIN_EMAIL=... ADMIN_PASSWORD=... python create_admin.py"""
import os
import sys

from app import User, bcrypt, create_app, db

email = os.getenv("ADMIN_EMAIL", "").strip().lower()
password = os.getenv("ADMIN_PASSWORD", "")
if "@" not in email or len(password) < 12:
    sys.exit("Set ADMIN_EMAIL and ADMIN_PASSWORD (at least 12 characters).")

app = create_app()
with app.app_context():
    user = User.query.filter_by(email=email).first()
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    if user:
        user.role, user.password = "admin", hashed
    else:
        db.session.add(User(name="Admin", email=email, password=hashed, role="admin"))
    db.session.commit()
    print(f"Admin ready: {email}")
