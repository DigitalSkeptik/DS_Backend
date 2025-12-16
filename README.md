# DS_Backend

## Startup

### 0. Clone repository
Just use `git clone`, and go to project directory, you know it...
Then create a `venv`

### 1. Install dependecies with [Poetry](https://python-poetry.org/docs/)
**USE BASH**
```bash
### Poetry install (python3.13)
pip install poetry
poetry install
```

!!! Note, be sure to use `python3.13` with either poetry or standard venv & pip.

### 2. Setup database and migrations

```bash
### Setup database
docker-compose up -d

### Run Alembic migrations
alembic upgrade head
```

### 3. Run app

```bash
uvicorn app.main:app --reload

```


## Versioning

API has two versions at this moment, `/v1` and `/v2`. Both versions expose Swagger and Redoc docs, e.g. `/v1/docs` for Swagger of API v1, and `/v2/redoc` for Redoc of API v2.

## Authentication

API uses JWT tokens with refresh tokens for authentication. It is used since our this API is designed only for one first party client, so we can just do authentication on our own. Another concern is that we need to pass user session data to billing (mock) service, so it is nore convenient to use tokens for this task.

### DEV
#### Making migrations
```bash
alembic revision --autogenerate -m "migration_name"

alembic upgrade head
```
