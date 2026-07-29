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
    *)
        echo "Usage: $0 {install|start}"
        exit 1
        ;;
esac
