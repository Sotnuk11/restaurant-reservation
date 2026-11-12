from app import create_app

app = create_app()  # gunicorn wsgi:app
