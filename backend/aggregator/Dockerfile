FROM python:3.10-slim

WORKDIR /app

# Copy the requirements file from the parent backend directory
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the common backend code from the parent backend directory
COPY common ./common
# Copy the specific service's code from the current context
COPY aggregator ./aggregator

ENV MODULE_NAME=backend.aggregator.main
ENV VARIABLE_NAME=app
ENV SERVICE_PORT=8002

EXPOSE 8002

CMD ["uvicorn", "aggregator.main:app", "--host", "0.0.0.0", "--port", "8002"]