import sqlite3
from pathlib import Path


def init_database() -> Path:
    root = Path(__file__).resolve().parents[2]
    DB_PATH = root / "ecommerce.db"
    SQL_SEED_PATH = root / "ecommerce_setup.sql"

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SQL_SEED_PATH.exists():
        raise FileNotFoundError(
            f"The SQL seed file was not found at: {SQL_SEED_PATH}"
        )

    sql_script = SQL_SEED_PATH.read_text(encoding="utf-8")

    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.executescript(sql_script)
        connection.commit()
    except sqlite3.Error as e:
        connection.rollback()
        raise e
    finally:
        connection.close()

    return DB_PATH


def main():
    try:
        db_path = init_database()
        print(f"Database successfully initialized at: {db_path}")
    except Exception as e:
        print(f"Database initialization failed: {e}")


if __name__ == "__main__":
    main()