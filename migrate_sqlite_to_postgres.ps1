param(
    [string]$FixturePath = "dumps\sqlite_to_postgres_fixture.json"
)

$ErrorActionPreference = "Stop"

Write-Host "1/4 Exporting data from SQLite..."
python manage.py dumpdata --settings=tech_site.settings_sqlite --exclude contenttypes --exclude auth.permission --output $FixturePath

Write-Host "2/4 Running PostgreSQL migrations..."
python manage.py migrate

Write-Host "3/4 Loading fixture into PostgreSQL..."
python manage.py loaddata $FixturePath

Write-Host "4/4 Verifying migrated data..."
python manage.py check

Write-Host "Migration completed."
