FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create data directory for SQLite (if using persistent volume)
RUN mkdir -p /data

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Start server (migrations run on startup to handle volume mount timing)
CMD python manage.py migrate --noinput && gunicorn bridgio.wsgi:application --bind 0.0.0.0:8000

