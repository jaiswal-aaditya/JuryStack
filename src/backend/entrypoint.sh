#!/bin/sh
set -eu

echo "running database migrations"
alembic upgrade head

echo "seeding fixture data"
python -m app.core.seed

echo "starting JuryStack API"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
