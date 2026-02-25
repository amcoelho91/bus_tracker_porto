import psycopg
from psycopg.rows import dict_row
from app.config import settings

def get_conn():
    # Create a new connection per request in API (simple and reliable).
    # For more throughput you can add pooling later.
    return psycopg.connect(settings.database_url, row_factory=dict_row)