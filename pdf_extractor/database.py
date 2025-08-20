import sqlite3
import logging
from typing import Dict, Any

DB_NAME = "data.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdf_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT,
                    branch_name TEXT,
                    account_number TEXT
                )
            """)
            conn.commit()
            logger.info("Baza danych została zainicjalizowana.")
    except sqlite3.Error as e:
        logger.error(f"Błąd podczas inicjalizacji bazy danych: {e}")
        raise


def save_data(data: Dict[str, Any]) -> None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pdf_data (customer_name, branch_name, account_number)
                VALUES (?, ?, ?)
                """,
                (
                    data.get("customer_name"),
                    data.get("branch_name"),
                    data.get("account_number"),
                ),
            )
            conn.commit()
            logger.info("Dane zostały zapisane do bazy.")
    except sqlite3.Error as e:
        logger.error(f"Błąd podczas zapisu do bazy: {e}")
        raise
    except KeyError as e:
        logger.error(f"Brak wymaganej wartości w danych wejściowych: {e}")
        raise
