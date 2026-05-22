#!/bin/sh
set -e

# Wait for database
if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Start Gunicorn
echo "Starting gunicorn..."
if [ -z "$GUNICORN_BIND" ]; then
    GUNICORN_BIND="0.0.0.0:8000"
fi

if [ -z "$GUNICORN_WORKERS" ]; then
    GUNICORN_WORKERS="$(python -c "import os; print((os.cpu_count() or 1) * 2 + 1)")"
fi

if [ -z "$GUNICORN_TIMEOUT" ]; then
    GUNICORN_TIMEOUT="30"
fi

exec gunicorn tech_site.wsgi:application --bind "$GUNICORN_BIND" --workers "$GUNICORN_WORKERS" --timeout "$GUNICORN_TIMEOUT"
