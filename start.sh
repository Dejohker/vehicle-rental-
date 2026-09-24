#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate --noinput
if [ "${SEED_DEMO_FLEET:-false}" = "true" ]; then
  python manage.py seed_data --fleet-only
  python manage.py seed_showcase
  python manage.py attach_showcase_images
fi
exec python -m gunicorn vehicle_rental.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}" --access-logfile - --error-logfile -
