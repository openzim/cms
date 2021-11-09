#!/bin/sh

echo "Running database migrations for ${DATABASE_URL}…"
alembic upgrade head
