from clickhouse_driver import Client
from config import settings
import logging

_client = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(
            host=settings.CH_HOST,
            port=settings.CH_PORT,
            database=settings.CH_DATABASE,
            user=settings.CH_USER,
            password=settings.CH_PASSWORD,
        )
    return _client


def execute(query: str, params: dict = None):
    client = get_client()
    try:
        return client.execute(query, params or {})
    except Exception as e:
        logging.error(f"ClickHouse execute error: {e}")
        raise


def insert(table: str, rows: list, column_names: list):
    """Batch insert rows into a ClickHouse table."""
    if not rows:
        return
    client = get_client()
    client.execute(
        f"INSERT INTO {table} ({', '.join(column_names)}) VALUES",
        rows,
    )
