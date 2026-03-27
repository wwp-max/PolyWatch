# data_pipeline/collector/db.py
import os
import psycopg2
import psycopg2.extras
from datetime import datetime

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://polywatch:polywatch@localhost:5432/polywatch",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def upsert_market(conn, token_id: str, slug: str, question: str) -> None:
    """Insert market if not exists. Ignore if already present."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO markets (token_id, slug, question)
            VALUES (%s, %s, %s)
            ON CONFLICT (token_id) DO NOTHING
            """,
            (token_id, slug, question),
        )
    conn.commit()


def insert_price_rows(conn, token_id: str, rows: list[dict]) -> int:
    """
    Bulk insert price rows. Silently skips duplicates.
    Returns number of rows actually inserted.
    """
    if not rows:
        return 0

    data = [(r["time"], token_id, r["price"]) for r in rows]

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO price_history (time, token_id, price)
            VALUES %s
            ON CONFLICT (time, token_id) DO NOTHING
            RETURNING time
            """,
            data,
        )
        inserted = len(cur.fetchall())

    conn.commit()
    return inserted


def get_latest_timestamp(conn, token_id: str) -> datetime | None:
    """Return the most recent time stored for token_id, or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(time) FROM price_history WHERE token_id = %s",
            (token_id,),
        )
        result = cur.fetchone()
        return result[0] if result and result[0] else None
