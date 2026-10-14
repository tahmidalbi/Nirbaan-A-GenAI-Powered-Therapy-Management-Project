import os

# Must be set before any app module creates its database engine or settings.
os.environ.setdefault("DATABASE_URL", "sqlite://")
