import sqlite3
import logging
from typing import Dict, Any
from pdf_extractor.config import INPUT_MAPPING

DB_NAME = "data.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db() -> None:
    """Initializes the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            fields = []
            for key in INPUT_MAPPING.keys():
                fields.append(f"{key} TEXT")

            create_table_sql = f"""
                CREATE TABLE pdf_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {", ".join(fields)}
                )
            """

            cursor.execute(create_table_sql)
            conn.commit()
            logger.info("Database initialized successfully.")

    except (sqlite3.Error, OSError) as e:
        logger.error(f"Error initializing database: {e}")
        raise


def save_data(data: Dict[str, Any]) -> None:
    """Saves data to the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values = list(data.values())

            cursor.execute(
                f"INSERT INTO pdf_data ({columns}) VALUES ({placeholders})", values
            )

            conn.commit()
            logger.info(f"Data saved: {data}")

    except sqlite3.Error as e:
        logger.error(f"Error saving data: {e}")
        raise
