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
    docker:up)
        echo "Building and starting Docker containers..."
        docker compose up --build
        ;;
    docker:down)
        echo "Stopping Docker containers..."
        docker compose down
        ;;
    docker:rebuild)
        echo "Rebuilding and restarting Docker containers..."
        docker compose up --build --force-recreate
        ;;
    *)
        echo "Usage: $0 {install|start|db:init|db:migrate|db:new-migration <message>|docker:up|docker:down|docker:rebuild}"
        exit 1
        ;;
esac
