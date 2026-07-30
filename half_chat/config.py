import os

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Shurik2010@localhost:5432/half_chat",
)
