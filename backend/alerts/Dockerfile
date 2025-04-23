FROM python:3.10-slim

WORKDIR /app

# Copy the requirements file from the parent backend directory
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the common backend code from the parent backend directory
COPY common ./common
# Copy the specific service's code from the current context
COPY alerts ./alerts

ENV MODULE_NAME=backend.alerts.main
ENV VARIABLE_NAME=app
ENV SERVICE_PORT=8004

EXPOSE 8004

CMD ["uvicorn", "alerts.main:app", "--host", "0.0.0.0", "--port", "8004"]