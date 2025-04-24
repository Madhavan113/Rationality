FROM python:3.10-slim

WORKDIR /app

# Copy requirements.txt
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy all code from the current context
COPY . .

# Create a Python package path for the common module
ENV PYTHONPATH=/app

ENV MODULE_NAME=main
ENV VARIABLE_NAME=app
ENV DEFAULT_PORT=8003

EXPOSE ${PORT:-8003}

# Use shell form to ensure environment variables are properly expanded
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8003}