#!/usr/bin/env python3
"""
Скрипт инициализации БД.
Создаёт базу данных и таблицы, если их нет.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg2  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import half_chat.models  # noqa: F401, E402
from half_chat.config import DATABASE_URL  # noqa: E402


def parse_url(url: str) -> dict:
    m = re.match(
        r"postgresql://(?:(.+?):(.+?)@)?(.+?):(\d+)/(.+)",
        url,
    )
    if not m:
        raise ValueError(f"Не удалось разобрать DATABASE_URL: {url}")
    user, password, host, port, dbname = m.groups()
    return {
        "user": user or "postgres",
        "password": password or "",
        "host": host or "localhost",
        "port": int(port) if port else 5432,
        "dbname": dbname or "half_chat",
    }


def create_database_if_not_exists(params: dict):
    conn = psycopg2.connect(
        host=params["host"],
        port=params["port"],
        user=params["user"],
        password=params["password"],
        dbname="postgres",
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (params["dbname"],))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{params["dbname"]}"')
        print(f"БД '{params['dbname']}' создана")
    else:
        print(f"БД '{params['dbname']}' уже существует")
    cur.close()
    conn.close()


def create_tables(database_url: str):
    engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    print("Таблицы созданы")


def main():
    database_url = os.getenv("DATABASE_URL", DATABASE_URL)
    print(f"Подключение: {database_url}")

    params = parse_url(database_url)
    create_database_if_not_exists(params)
    create_tables(database_url)


if __name__ == "__main__":
    main()
