#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

case "${1:-}" in
    install)
        echo "Installing dependencies..."
        poetry install --no-root
        ;;
    start)
        echo "Starting server..."
        poetry run uvicorn main:app --reload --host 0.0.0.0
        ;;
    db:init)
        echo "Initializing database..."
        poetry run python scripts/init_db.py
        ;;
    db:migrate)
        echo "Running migrations..."
        poetry run alembic upgrade head
        ;;
    db:new-migration)
        shift
        poetry run alembic revision --autogenerate -m "${1:-auto}"
        ;;
    *)
        echo "Usage: $0 {install|start|db:init|db:migrate|db:new-migration <message>}"
        exit 1
        ;;
esac
