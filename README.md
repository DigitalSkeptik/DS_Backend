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


### DEV
#### Making migrations
```bash
alembic revision --autogenerate -m "migration_name"

alembic upgrade head
```