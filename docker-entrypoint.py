#!/usr/bin/env python3
"""Docker entrypoint: create DB if missing, run migrations, then start the app."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def _connect(parsed, dbname: str):
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password or "",
        dbname=dbname,
        connect_timeout=3,
    )


def ensure_database(database_url: str, attempts: int = 30, delay: float = 1.0) -> None:
    parsed = urlparse(database_url)
    dbname = (parsed.path or "").lstrip("/").split("?")[0]
    if not dbname or not dbname.replace("_", "").isalnum():
        raise SystemExit(f"Некорректное имя БД в DATABASE_URL: {dbname!r}")

    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            conn = _connect(parsed, dbname)
            conn.close()
            print(f"БД '{dbname}' уже существует", flush=True)
            return
        except psycopg2.OperationalError as exc:
            last_error = exc
            message = str(exc)
            if "does not exist" not in message:
                time.sleep(delay)
                continue

            created = False
            for admin_db in ("postgres", "template1"):
                try:
                    admin = _connect(parsed, admin_db)
                except psycopg2.OperationalError:
                    continue
                admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                with admin.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s",
                        (dbname,),
                    )
                    if not cur.fetchone():
                        cur.execute(f'CREATE DATABASE "{dbname}"')
                        print(f"БД '{dbname}' создана", flush=True)
                    else:
                        print(f"БД '{dbname}' уже существует", flush=True)
                admin.close()
                created = True
                break
            if created:
                return
            time.sleep(delay)

    raise SystemExit(f"Не удалось подготовиться к БД: {last_error}")


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL не задан")

    ensure_database(database_url)
    subprocess.check_call(["alembic", "upgrade", "head"])

    if len(sys.argv) < 2:
        raise SystemExit("Не передана команда запуска")
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
