import os
from urllib.parse import parse_qs, unquote, urlparse


def _parse_database_url():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return None

    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use the postgres:// or postgresql:// scheme.")

    query = parse_qs(parsed.query)
    settings = {
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "127.0.0.1",
        "PORT": str(parsed.port or 5432),
        "OPTIONS": {},
    }
    if query.get("sslmode"):
        settings["OPTIONS"]["sslmode"] = query["sslmode"][0]
    return settings


def get_database_settings():
    url_settings = _parse_database_url()
    if url_settings:
        return url_settings

    options = {}
    sslmode = os.getenv("POSTGRES_SSLMODE") or os.getenv("DB_SSLMODE")
    if sslmode:
        options["sslmode"] = sslmode

    return {
        "NAME": os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "tech")),
        "USER": os.getenv("POSTGRES_USER", os.getenv("DB_USER", "postgres")),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "")),
        "HOST": os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "127.0.0.1")),
        "PORT": str(os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432"))),
        "OPTIONS": options,
    }


def get_django_database_config():
    settings = get_database_settings()
    config = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": settings["NAME"],
            "USER": settings["USER"],
            "PASSWORD": settings["PASSWORD"],
            "HOST": settings["HOST"],
            "PORT": settings["PORT"],
        }
    }
    if settings["OPTIONS"]:
        config["default"]["OPTIONS"] = settings["OPTIONS"]
    return config


def _import_postgres_driver():
    try:
        import psycopg

        return psycopg
    except ImportError:
        import psycopg2

        return psycopg2


class CursorWrapper:
    def __init__(self, connection_wrapper, inner_cursor):
        self._connection_wrapper = connection_wrapper
        self._inner_cursor = inner_cursor
        self._lastrowid = None

    def execute(self, query, params=None):
        normalized_query = query.replace("?", "%s")
        if params is None:
            self._inner_cursor.execute(normalized_query)
        else:
            self._inner_cursor.execute(normalized_query, params)

        self._lastrowid = getattr(self._inner_cursor, "lastrowid", None)
        if normalized_query.lstrip().upper().startswith("INSERT") and self._lastrowid is None:
            self._lastrowid = self._connection_wrapper.fetch_lastval()
        return self

    def executemany(self, query, param_list):
        normalized_query = query.replace("?", "%s")
        self._inner_cursor.executemany(normalized_query, param_list)
        self._lastrowid = None
        return self

    @property
    def lastrowid(self):
        return self._lastrowid

    def __iter__(self):
        return iter(self._inner_cursor)

    def __getattr__(self, name):
        return getattr(self._inner_cursor, name)


class ConnectionWrapper:
    def __init__(self, inner_connection):
        self._inner_connection = inner_connection

    def cursor(self):
        return CursorWrapper(self, self._inner_connection.cursor())

    def fetch_lastval(self):
        aux_cursor = self._inner_connection.cursor()
        try:
            aux_cursor.execute("SELECT LASTVAL()")
            row = aux_cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None
        finally:
            aux_cursor.close()

    def __getattr__(self, name):
        return getattr(self._inner_connection, name)


def connect_db():
    driver = _import_postgres_driver()
    settings = get_database_settings()
    connect_kwargs = {
        "dbname": settings["NAME"],
        "user": settings["USER"],
        "password": settings["PASSWORD"],
        "host": settings["HOST"],
        "port": settings["PORT"],
    }
    connect_kwargs.update(settings["OPTIONS"])
    return ConnectionWrapper(driver.connect(**connect_kwargs))
