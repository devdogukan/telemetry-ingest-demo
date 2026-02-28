# 🌡️ Telemetry Collection System with Celery & Batch Processing

High-performance, scalable telemetry data collection system. Optimizes database write operations with batch processing using Flask, Celery, Redis, and PostgreSQL.

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Performance](#-performance)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Endpoints](#-api-endpoints)
- [Project Structure](#-project-structure)
- [Technologies](#-technologies)
- [Configuration](#-configuration)

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│  (Load Test)│
└──────┬──────┘
       │ HTTP POST
       ▼
┌─────────────────┐
│  Flask API      │
│  /api/telemetry │
└────────┬────────┘
         │ enqueue_telemetry.delay()
         ▼
┌─────────────────┐
│  Redis Buffer   │  ← telemetry_buffer (list)
│  (In-Memory)    │
└────────┬────────┘
         │ Every 5 seconds
         │ Batch of 100 items
         ▼
┌─────────────────┐
│  Celery Worker  │
│  process_buffer │
└────────┬────────┘
         │ Bulk insert
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  telemetries    │
└─────────────────┘
```

### Workflow

1. **Data Collection**: Client sends telemetry data to Flask API
2. **Queuing**: Data is quickly added to Redis buffer (rpush)
3. **Acknowledgment**: API immediately returns 202 (Accepted)
4. **Batch Processing**: Celery Beat triggers every 5 seconds
5. **Bulk Insert**: Worker takes max 100 records from Redis and writes to PostgreSQL
6. **Persistence**: Data is permanently saved to database

### Why Batch Processing?

**Traditional Approach (1 DB write per request):**
```
5000 requests = 5000 DB connections + 5000 INSERT queries
Slow, heavy load on database
```

**Batch Processing Approach:**
```
5000 requests → Redis buffer (very fast)
50 batches × 100 INSERTs = 50 DB connections
10-100x faster, database-friendly
```

## 📊 Performance

### Load Test Results

**Test Parameters:**
- Total Requests: **5,000**
- Concurrency: **50**
- Batch Size: **100**
- Batch Interval: **5 seconds**

**Results:**
```
📊 Overall Statistics:
  Total Requests:        5,000
  Successful:            5,000 (100.00%)
  Failed:                0 (0.00%)
  Total Duration:        37.49s
  Requests per Second:   133.37

⏱️  Latency Statistics (ms):
  Mean:                  373.06
  Median:                361.34
  Std Dev:               191.65
  Min:                   57.91
  Max:                   1606.09

📈 Percentiles (ms):
  P50:                   361.34
  P90:                   624.18
  P95:                   693.18
  P99:                   1004.69

📋 HTTP Status Codes:
  202: 5,000 (100.00%)

✅ EXCELLENT: >99% success rate
```

### Database Performance

```sql
-- Database state after test
SELECT COUNT(*) FROM telemetries;
 count
-------
  5005     -- 5000 test + 5 sample data
```

### Worker Performance

```
Processing batch of 100 items from buffer (total: 600)
Successfully inserted batch of 100 telemetries
Task succeeded in 0.035s
```

**Sample batch processing time**: ~35ms / 100 records = **0.35ms per record**

## 🚀 Installation

### Requirements

- Python 3.11+
- Docker & Docker Compose
- uv (Python package manager) or pip

### 1. Clone the Repository

```bash
git clone https://github.com/devdogukan/telemetry-ingest-demo
cd telemetry-ingest-demo
```

### 2. Create Environment File

Create a `.env` file:

```env
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=book_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Batch Processing Configuration
REDIS_BUFFER_KEY=telemetry_buffer
REDIS_BULK_SIZE=100
REDIS_BULK_INTERVAL=5

# Database Pool Configuration
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
```

### 3. Start Docker Services

```bash
docker-compose up -d
```

This command starts:
- PostgreSQL (port 5432)
- Redis (port 6379)

### 4. Install Python Dependencies

**With uv (recommended):**
```bash
uv sync
```

**With pip:**
```bash
pip install -r requirements.txt
# or
pip install celery[redis] flask psycopg[binary,pool] python-dotenv requests
```

### 5. Initialize Database

```bash
# Create table and insert sample data
python -m flask_app.init_db

# Alternative
uv run init_db.py
```

Output:
```
2026-02-28 12:33:54,161 - INFO - Connecting to database...
2026-02-28 12:33:54,246 - INFO - Dropping existing telemetries table if exists...
2026-02-28 12:33:54,248 - INFO - Creating telemetries table...
2026-02-28 12:33:54,251 - INFO - Creating index on sensor_id...
2026-02-28 12:33:54,254 - INFO - Inserting sample data...
2026-02-28 12:33:54,289 - INFO - ✅ Database initialized successfully!
```

## 🎯 Usage

### 1. Start Flask API

```bash
# Development mode
python run.py

# Production mode (with gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 "flask_app:create_app()"
```

API runs at: `http://localhost:5000`

### 2. Start Celery Worker

```bash
# Worker + Beat scheduler (for periodic tasks)
celery -A flask_app.tasks_with_batch worker --beat --loglevel=info

# Worker only
celery -A flask_app.tasks_with_batch worker --loglevel=info

# Beat scheduler only (separate process)
celery -A flask_app.tasks_with_batch beat --loglevel=info
```

**Alternative (with uv):**
```bash
uv run celery -A flask_app.tasks_with_batch worker --beat --loglevel=info
```

### 3. Manual Testing

```bash
# Send a single telemetry record
curl -X POST http://localhost:5000/api/telemetry \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": "room_24", "temperature": 22.5}'

# Response
{"status": "queued", "message": "Data receiving"}
```

### 4. Run Load Test

```bash
# Send 5000 requests (50 concurrent)
python load_test.py

# Alternative
uv run load_test.py
```

### 5. Check Database

```bash
# Connect to PostgreSQL
docker exec -it celery-postgres psql -U postgres -d book_db
```
```sql
# Query data
book_db=# SELECT COUNT(*) FROM telemetries;
book_db=# SELECT * FROM telemetries ORDER BY recorded_at DESC LIMIT 10;
book_db=# SELECT sensor_id, COUNT(*) FROM telemetries GROUP BY sensor_id;
```

## 📡 API Endpoints

### POST /api/telemetry

Send telemetry data.

**Request:**
```json
{
  "sensor_id": "room_24",
  "temperature": 22.5
}
```

**Response:**
```json
{
  "status": "queued",
  "message": "Data receiving"
}
```

**Status Codes:**
- `202 Accepted`: Data successfully queued
- `400 Bad Request`: Invalid data format
- `500 Internal Server Error`: Server error

**Example Usage (Python):**
```python
import requests

response = requests.post(
    "http://localhost:5000/api/telemetry",
    json={"sensor_id": "sensor_1", "temperature": 25.3}
)
print(response.json())
```

## 📁 Project Structure

```
celery-python/
├── flask_app/                      # Main application package
│   ├── __init__.py                 # Flask app factory
│   ├── config.py                   # Configuration class
│   ├── routes.py                   # API routes
│   ├── tasks.py                    # Simple Celery tasks
│   └── tasks_with_batch.py         # Batch processing tasks
│
├── init_db.py                      # Database initialization script
├── run.py                          # Flask development server
├── load_test.py                    # Load testing script
│
├── docker-compose.yml              # Docker services (Redis, PostgreSQL)
├── pyproject.toml                  # Python dependencies (uv)
├── .env                            # Environment variables
│
└── README.md                       # This file
```

### Key Files

- **[flask_app/tasks_with_batch.py](flask_app/tasks_with_batch.py)**: Batch processing logic
- **[flask_app/config.py](flask_app/config.py)**: All configuration variables
- **[load_test.py](load_test.py)**: Detailed performance testing tool
- **[init_db.py](init_db.py)**: Database schema and sample data

## 🛠️ Technologies

### Backend
- **[Flask](https://flask.palletsprojects.com/)**: Web framework
- **[Celery](https://docs.celeryq.dev/)**: Distributed task queue
- **[Redis](https://redis.io/)**: Message broker & buffer
- **[PostgreSQL](https://www.postgresql.org/)**: Relational database

### Python Libraries
- **[psycopg3](https://www.psycopg.org/psycopg3/)**: PostgreSQL adapter
- **[psycopg_pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)**: Connection pooling
- **[python-dotenv](https://pypi.org/project/python-dotenv/)**: Environment variable management
- **[requests](https://requests.readthedocs.io/)**: HTTP library (load testing)

### Development Tools
- **[uv](https://github.com/astral-sh/uv)**: Fast Python package manager
- **[Docker](https://www.docker.com/)**: Containerization
- **[Docker Compose](https://docs.docker.com/compose/)**: Multi-container orchestration

## ⚙️ Configuration

### Batch Processing Settings

```python
# flask_app/config.py
REDIS_BUFFER_KEY = "telemetry_buffer"     # Redis buffer key
REDIS_BULK_SIZE = 100                     # Batch size
REDIS_BULK_INTERVAL = 5                   # Batch interval (seconds)
```

**Optimization Tips:**
- **Low latency**: `REDIS_BULK_SIZE=50`, `REDIS_BULK_INTERVAL=2`
- **High throughput**: `REDIS_BULK_SIZE=500`, `REDIS_BULK_INTERVAL=10`
- **Balanced**: `REDIS_BULK_SIZE=100`, `REDIS_BULK_INTERVAL=5` (default)

### Database Connection Pool

```python
DB_POOL_MIN_SIZE = 2    # Minimum number of connections
DB_POOL_MAX_SIZE = 10   # Maximum number of connections
```

### Celery Settings

```python
# flask_app/tasks_with_batch.py
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,        # 30 minutes
    task_soft_time_limit=25 * 60,   # 25 minutes
)
```

## 🔍 Monitoring

### Celery Worker Logs

```bash
# Monitor worker logs
celery -A flask_app.tasks_with_batch worker --loglevel=debug

# Example output
[2026-02-28 15:40:15,832: INFO/ForkPoolWorker-7] Processing batch of 100 items from buffer (total: 600)
[2026-02-28 15:40:15,864: INFO/ForkPoolWorker-7] Successfully inserted batch of 100 telemetries
[2026-02-28 15:40:15,865: INFO/ForkPoolWorker-7] Task succeeded in 0.035s: {'processed': 100, 'status': 'success', 'remaining': 500}
```

### Redis Buffer Status

```bash
# Connect to Redis CLI
docker exec -it celery-redis redis-cli

# Check buffer length
127.0.0.1:6379> SELECT 1
127.0.0.1:6379[1]> LLEN telemetry_buffer
(integer) 350

# Show buffer contents (first 5 elements)
127.0.0.1:6379[1]> LRANGE telemetry_buffer 0 4
```

### Database Statistics

```sql
-- Total record count
SELECT COUNT(*) FROM telemetries;

-- Record count per sensor
SELECT sensor_id, COUNT(*) as count 
FROM telemetries 
GROUP BY sensor_id 
ORDER BY count DESC 
LIMIT 10;

-- Records in the last hour
SELECT COUNT(*) 
FROM telemetries 
WHERE recorded_at > NOW() - INTERVAL '1 hour';

-- Average temperature
SELECT AVG(temperature) as avg_temp, 
       MIN(temperature) as min_temp, 
       MAX(temperature) as max_temp 
FROM telemetries;
```

## 📝 License

This project is for educational purposes.

---

**Developer**: [@devdogukan](https://github.com/devdogukan)  
**Last Updated**: February 28, 2026
