FROM python:3.10-slim

WORKDIR /app

# Copy requirements.txt
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy all code from the current context
COPY . .

# Create a Python package path for the common module
ENV PYTHONPATH=/app

# Default port if not provided by Railway
ENV DEFAULT_PORT=8004

EXPOSE ${PORT:-8004}

# Use shell form to ensure environment variables are properly expanded
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8004}