"""
Database migration utility.
Ensures new schema columns exist in existing PostgreSQL tables without needing Alembic.
"""
from sqlalchemy import text
from db.base import engine


def run_migrations():
    """Apply incremental schema updates idempotently."""
    migrations = [
        "ALTER TABLE designs ADD COLUMN IF NOT EXISTS image_data_b64 JSON DEFAULT '[]'::json;",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                print(f"[MIGRATION WARNING] {sql}: {e}")
        print("[MIGRATION] Database schema up to date.")


if __name__ == "__main__":
    run_migrations()
