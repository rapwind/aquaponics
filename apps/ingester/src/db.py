import psycopg

from config import PGDATABASE, PGHOST, PGPASSWORD, PGPORT, PGUSER


def get_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        autocommit=True,
    )


INSERT_SQL = """
INSERT INTO sensor_metrics
  (ts, tank_id, device_id, sensor_group, metric_name, value, unit, status, topic, raw_payload)
VALUES
  (%(ts)s, %(tank_id)s, %(device_id)s, %(sensor_group)s, %(metric_name)s, %(value)s, %(unit)s, %(status)s, %(topic)s, %(raw_payload)s::jsonb)
"""


def insert_rows(conn: psycopg.Connection, rows: list[dict]) -> None:
    if not rows:
        return

    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)
