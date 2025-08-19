import os
import sqlite3
import pytest

from pdf_extractor import database

TEMP_DB = "test_data.db"


@pytest.fixture(autouse=True)
def temp_db_setup_and_teardown() -> None:
    """Podmienia DB_NAME na tymczasową bazę przed testem i sprząta po teście."""
    old_db_name = database.DB_NAME
    database.DB_NAME = TEMP_DB

    if os.path.exists(TEMP_DB):
        os.remove(TEMP_DB)
    yield

    if os.path.exists(TEMP_DB):
        os.remove(TEMP_DB)
    database.DB_NAME = old_db_name


def test_init_db_creates_table() -> None:
    database.init_db()
    conn = sqlite3.connect(TEMP_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pdf_data'"
    )
    table = cursor.fetchone()
    assert table is not None
    conn.close()


def test_save_data_inserts_row() -> None:
    database.init_db()
    sample_data = {
        "customer_name": "John Doe",
        "branch_name": "Main",
        "account_number": "12345",
    }
    database.save_data(sample_data)

    conn = sqlite3.connect(TEMP_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name, branch_name, account_number FROM pdf_data")
    row = cursor.fetchone()
    assert row == (
        sample_data["customer_name"],
        sample_data["branch_name"],
        sample_data["account_number"],
    )
    conn.close()
