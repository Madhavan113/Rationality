# Polymarket Monitor

A comprehensive platform for monitoring and analyzing Polymarket prediction markets.

## Overview

This project consists of a React frontend and a set of FastAPI microservices that provide:

- Real-time market data ingestion from Polymarket
- Price aggregation and true price calculation 
- Trader performance tracking and leaderboard
- Price deviation alerts
- Market rationality analysis

## Architecture

The system is composed of the following components:

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend Services**:
  - **Ingestion Service**: Fetches market data from Polymarket
  - **Aggregator Service**: Computes true prices from market data
  - **Leaderboard Service**: Tracks trader performance
  - **Alerts Service**: Monitors price deviations and sends notifications
  - **Rationality Service**: Analyzes trader behavior for rationality

- **Infrastructure**:
  - Redis for real-time data storage
  - PostgreSQL with TimescaleDB for time-series data
  - Docker Compose for local development
  - GitHub Actions for CI/CD

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.10+ (for local backend development)

### Running Locally

1. Clone the repository:
   ```
   git clone <repository-url>
   cd polymarket-monitor
   ```

2. Start all services with Docker Compose:
   ```
   docker-compose up -d
   ```

3. The frontend will be available at http://localhost:3000

### Development

#### Frontend Development

```
cd frontend
npm install
npm run dev
```

#### Backend Development

```
cd backend
pip install -r requirements.txt
cd <service-directory>  # e.g., cd ingestion
uvicorn main:app --reload --port <port>  # e.g., 8001 for ingestion
```

## Rationality Service API

The rationality service analyzes market data to compute rationality metrics for traders.

### Endpoints

#### GET `/api/v1/rationality/active/{marketId}`

Returns rationality metrics based on active orders in the specified market.

**Response:**
```json
{
  "marketId": "string",
  "computedAt": 1625097600000,
  "overallScore": 0.75,
  "perTraderScore": {
    "0x123abc...": 0.8,
    "0x456def...": 0.7
  }
}
```

#### GET `/api/v1/rationality/historical/{marketId}`

Returns rationality metrics based on historical trades in the specified market.

**Response:**
```json
{
  "marketId": "string",
  "computedAt": 1625097600000,
  "overallScore": 0.65,
  "perTraderScore": {
    "0x123abc...": 0.7,
    "0x789ghi...": 0.6
  }
}
```

## License

MIT 