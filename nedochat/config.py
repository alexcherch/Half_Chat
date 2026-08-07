import os

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

env_url = os.getenv("DATABASE_URL")
if env_url:
    DATABASE_URL = env_url
else:
    try:
        from nedochat.db_config import DATABASE_URL
    except ImportError:
        DATABASE_URL = "postgresql://user:password@localhost:5432/nedochat"
