# PostgreSQL Migration

## Required environment

Set either `DATABASE_URL` or the `POSTGRES_*` variables from `.env.example`.

Example:

```env
POSTGRES_DB=tech
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

## Install driver

```powershell
python -m pip install "psycopg[binary]"
```

## Run migration

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_sqlite_to_postgres.ps1
```

The script:

1. Exports data from `db.sqlite3` using `tech_site.settings_sqlite`
2. Applies migrations to PostgreSQL
3. Imports the exported fixture into PostgreSQL
4. Runs `python manage.py check`
