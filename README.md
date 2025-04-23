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

### Environment Variables

#### Required Environment Variables:

Create a `.env` file in the root directory with the following variables:

```bash
# Supabase Backend Configuration
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co:5432/postgres
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Email Configuration (for Alerts Service)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your_smtp_password
EMAIL_FROM=alerts@example.com
```

For local frontend development, create a `.env.local` file in the `frontend` directory with:

```bash
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

These Vite environment variables are required for the frontend to connect to Supabase for real-time updates.

### Running Locally

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd polymarket-monitor
   ```

2. Start all services with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. The frontend will be available at http://localhost:3000

### Development

#### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

#### Backend Development

```bash
cd backend
pip install -r requirements.txt
cd <service-directory>  # e.g., cd ingestion
uvicorn main:app --reload --port <port>  # e.g., 8001 for ingestion
```

## Supabase Realtime Setup

To enable the frontend to receive real-time updates for true prices without needing a custom WebSocket connection from the aggregator service, configure Supabase Realtime:

1. **Enable Row Level Security (RLS)** for the `true_prices` table in your Supabase dashboard or via SQL:
    ```sql
    ALTER TABLE public.true_prices ENABLE ROW LEVEL SECURITY;
    ```

2. **Create an RLS Policy** allowing public read access (adjust as needed for your security requirements):
    ```sql
    CREATE POLICY public_read_true_prices
    ON public.true_prices
    FOR SELECT
    USING (true);
    ```

3. **Create a Supabase Publication** that includes the `true_prices` table. Supabase often creates a default `supabase_realtime` publication, but you can verify or create one:
    ```sql
    -- Check existing publications
    -- SELECT * FROM pg_publication;

    -- Create or add the table to the publication
    CREATE PUBLICATION supabase_realtime FOR TABLE public.true_prices;
    -- Or add if publication exists: ALTER PUBLICATION supabase_realtime ADD TABLE public.true_prices;
    ```

4. **Frontend Subscription**: In your frontend code (e.g., `TruePriceChart.tsx`), use the `supabase-js` client to subscribe to inserts on the `true_prices` table. See the comment in `backend/aggregator/main.py` for an example snippet.

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