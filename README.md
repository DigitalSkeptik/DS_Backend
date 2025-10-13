# DS_Backend

## Startup

### 0. Clone repository
Just use `git clone`, and go to project directory, you know it...

### 1. Install dependecies with [Poetry](https://python-poetry.org/docs/)
```bash
### Poetry install (python3.13)
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
