SECRET_KEY = "super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

SQLITE_FILE_NAME = "chat.db"
SQLITE_URL = f"sqlite:///{SQLITE_FILE_NAME}"
CONNECT_ARGS = {"check_same_thread": False, "timeout": 30}
