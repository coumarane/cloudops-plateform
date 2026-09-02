import os

os.environ.setdefault("CLOUDOPS_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CLOUDOPS_CELERY_EAGER", "true")
os.environ.setdefault("CLOUDOPS_AWS_ENABLED", "false")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

from app.db.session import init_db

init_db()
